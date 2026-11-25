"""The model behind every codelab.

Two implementations share one method, ``stream(system, messages, tools=None)``.
It yields small dict events, so a server never needs to know which model runs:

    {"type": "text", "text": "..."}                         a piece of reply text
    {"type": "tool_start", "id": "...", "name": "..."}      a tool call begins
    {"type": "tool_delta", "id": "...", "json": "..."}      a piece of its JSON input
    {"type": "tool_end", "id": "...", "name": "...", "input": {...}}
    {"type": "done", "stop_reason": "...", "content": [...], "usage": {...}}

``ScriptedLLM`` (the default) replays the reply that a codelab wrote down in its
``agent.py``. It streams that reply in small chunks with a short delay, so
progressive rendering is visible and every run prints the same output. Tests
and recorded demos use it; it never touches the network.

``ClaudeLLM`` sends the same system prompt and messages to the Claude API.
Turn it on with ``GENUI_LIVE=1`` and credentials in ``ANTHROPIC_API_KEY``.
Live runs cost money and their output differs from the recorded demos.

Messages use the Anthropic Messages format in both cases:
``{"role": "user" | "assistant", "content": str | [blocks]}``.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Callable, Iterator

DELAY = float(os.environ.get("GENUI_DELAY", "0.012"))  # seconds between scripted chunks
CHUNK = int(os.environ.get("GENUI_CHUNK", "28"))  # characters per scripted chunk


def text(value: str) -> dict:
    """A text content block."""
    return {"type": "text", "text": value}


def tool(name: str, input: dict, id: str | None = None) -> dict:
    """A tool_use content block, the shape the Messages API returns."""
    return {"type": "tool_use", "id": id or f"toolu_{uuid.uuid4().hex[:12]}", "name": name, "input": input}


def chunks(value: str, size: int = CHUNK) -> Iterator[str]:
    for start in range(0, len(value), size):
        yield value[start:start + size]


def last_user_text(messages: list[dict]) -> str:
    """The text of the most recent user message (tool results are skipped)."""
    for message in reversed(messages):
        if message["role"] != "user":
            continue
        content = message["content"]
        if isinstance(content, str):
            return content
        texts = [b.get("text", "") for b in content if b.get("type") == "text"]
        if texts:
            return "\n".join(texts)
    return ""


def tool_results(messages: list[dict]) -> list[dict]:
    """The tool_result blocks of the most recent user message.

    Empty when that message also carries new user text: a scripted model
    should answer the new question, not the old results.
    """
    if not messages or messages[-1]["role"] != "user" or isinstance(messages[-1]["content"], str):
        return []
    blocks = messages[-1]["content"]
    if any(b.get("type") == "text" and b.get("text") for b in blocks):
        return []
    return [b for b in blocks if b.get("type") == "tool_result"]


class ScriptedLLM:
    """Replays scripted replies. ``respond(system, messages)`` returns the blocks."""

    name = "scripted"

    def __init__(self, respond: Callable[[str, list[dict]], list[dict] | str], delay: float | None = None):
        self.respond = respond
        self.delay = DELAY if delay is None else delay
        self.calls: list[dict] = []

    def _pause(self):
        if self.delay:
            time.sleep(self.delay)

    def stream(self, system: str, messages: list[dict], tools: list[dict] | None = None) -> Iterator[dict]:
        self.calls.append({"system": system, "messages": [dict(m) for m in messages], "tools": tools})
        blocks = self.respond(system, messages)
        if isinstance(blocks, str):
            blocks = [text(blocks)]
        out_chars = 0
        for block in blocks:
            if block["type"] == "text":
                for piece in chunks(block["text"]):
                    self._pause()
                    out_chars += len(piece)
                    yield {"type": "text", "text": piece}
            elif block["type"] == "tool_use":
                yield {"type": "tool_start", "id": block["id"], "name": block["name"]}
                for piece in chunks(json.dumps(block["input"])):
                    self._pause()
                    out_chars += len(piece)
                    yield {"type": "tool_delta", "id": block["id"], "json": piece}
                yield {"type": "tool_end", "id": block["id"], "name": block["name"], "input": block["input"]}
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        yield {"type": "done", "stop_reason": stop, "content": blocks,
               "usage": {"output_chars": out_chars, "model": self.name}}


class ClaudeLLM:
    """Streams from the Claude API and maps its events onto the shared shape."""

    name = "claude"

    def __init__(self, model: str | None = None):
        import anthropic  # imported lazily: offline runs never need the SDK

        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("GENUI_MODEL", "claude-opus-5-5")
        self.effort = os.environ.get("GENUI_EFFORT", "low")  # UI generation: keep latency low

    def stream(self, system: str, messages: list[dict], tools: list[dict] | None = None) -> Iterator[dict]:
        kwargs = dict(
            model=self.model,
            max_tokens=64000,
            system=system,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort},
            # If a safety classifier declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if tools:
            # Stream tool inputs as they are generated; the caller validates them.
            kwargs["tools"] = [{**t, "eager_input_streaming": True} for t in tools]
        current = None
        with self.client.beta.messages.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "text":
                    yield {"type": "text", "text": event.text}
                elif event.type == "content_block_start" and event.content_block.type == "tool_use":
                    current = event.content_block
                    yield {"type": "tool_start", "id": current.id, "name": current.name}
                elif event.type == "input_json" and current is not None:
                    yield {"type": "tool_delta", "id": current.id, "json": event.partial_json}
            final = stream.get_final_message()
        # Keep every block (thinking blocks included) so the next turn can send them back unchanged.
        content = [block.model_dump(exclude_none=True) for block in final.content]
        for block in content:
            if block["type"] == "tool_use":
                yield {"type": "tool_end", "id": block["id"], "name": block["name"], "input": block["input"]}
        yield {"type": "done", "stop_reason": final.stop_reason, "content": content,
               "usage": {"input_tokens": final.usage.input_tokens, "output_tokens": final.usage.output_tokens,
                         "model": self.model}}


def get_llm(respond: Callable[[str, list[dict]], list[dict] | str]):
    """ClaudeLLM when GENUI_LIVE=1, otherwise a ScriptedLLM that calls ``respond``."""
    if os.environ.get("GENUI_LIVE") == "1":
        return ClaudeLLM()
    return ScriptedLLM(respond)


def reply_text(events: Iterator[dict]) -> tuple[str, dict]:
    """Drain a stream; return the joined text and the final ``done`` event."""
    parts, done = [], {}
    for event in events:
        if event["type"] == "text":
            parts.append(event["text"])
        elif event["type"] == "done":
            done = event
    return "".join(parts), done
