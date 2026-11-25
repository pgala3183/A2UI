"""AG-UI on the server: typed events over Server-Sent Events.

AG-UI (Agent-User Interaction protocol, https://docs.ag-ui.com) is the
transport between an agent and a frontend. The frontend POSTs a
``RunAgentInput`` (thread, run, messages, state, frontend tools, context);
the agent answers with a stream of events, one JSON object per SSE frame:

    RUN_STARTED  ...  TEXT_MESSAGE_START / _CONTENT / _END
                      TOOL_CALL_START / _ARGS / _END / TOOL_CALL_RESULT
                      STATE_SNAPSHOT / STATE_DELTA (JSON Patch)
                      STEP_STARTED / STEP_FINISHED, CUSTOM
                 ...  RUN_FINISHED (or RUN_ERROR)

Field names are camelCase on the wire, as in the official SDKs
(``ag-ui-protocol`` on PyPI, ``@ag-ui/client`` on npm). This module writes
the events by hand so every field is visible; ``test_shared.py`` checks them
against the official Pydantic models when ``ag-ui-protocol`` is installed.
"""

from __future__ import annotations

import json
import time
import uuid


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def event(type_: str, **fields) -> dict:
    return {"type": type_, "timestamp": int(time.time() * 1000), **fields}


def run_started(thread_id, run_id):
    return event("RUN_STARTED", threadId=thread_id, runId=run_id)


def run_finished(thread_id, run_id, result=None):
    return event("RUN_FINISHED", threadId=thread_id, runId=run_id, **({"result": result} if result is not None else {}))


def run_error(message, code=None):
    return event("RUN_ERROR", message=message, **({"code": code} if code else {}))


def step_started(name):
    return event("STEP_STARTED", stepName=name)


def step_finished(name):
    return event("STEP_FINISHED", stepName=name)


def text_start(message_id):
    return event("TEXT_MESSAGE_START", messageId=message_id, role="assistant")


def text_content(message_id, delta):
    return event("TEXT_MESSAGE_CONTENT", messageId=message_id, delta=delta)


def text_end(message_id):
    return event("TEXT_MESSAGE_END", messageId=message_id)


def tool_start(call_id, name, parent_message_id=None):
    return event("TOOL_CALL_START", toolCallId=call_id, toolCallName=name,
                 **({"parentMessageId": parent_message_id} if parent_message_id else {}))


def tool_args(call_id, delta):
    return event("TOOL_CALL_ARGS", toolCallId=call_id, delta=delta)


def tool_end(call_id):
    return event("TOOL_CALL_END", toolCallId=call_id)


def tool_result(call_id, content):
    return event("TOOL_CALL_RESULT", messageId=_id("msg"), toolCallId=call_id, role="tool",
                 content=content if isinstance(content, str) else json.dumps(content))


def state_snapshot(snapshot):
    return event("STATE_SNAPSHOT", snapshot=snapshot)


def state_delta(ops):
    return event("STATE_DELTA", delta=ops)


def custom(name, value):
    return event("CUSTOM", name=name, value=value)


class RunInput:
    """The body of an AG-UI run request (``RunAgentInput``)."""

    def __init__(self, body: dict):
        self.thread_id = body.get("threadId") or _id("thread")
        self.run_id = body.get("runId") or _id("run")
        self.state = body.get("state") or {}
        self.messages = body.get("messages") or []
        self.tools = body.get("tools") or []
        self.context = body.get("context") or []
        self.forwarded = body.get("forwardedProps") or {}
        for message in self.messages:
            if message.get("role") not in ("user", "assistant", "system", "developer", "tool"):
                raise ValueError(f"bad message role {message.get('role')!r}")

    def anthropic_messages(self) -> list[dict]:
        """AG-UI messages -> Messages API turns (tool calls and results become blocks)."""
        out: list[dict] = []

        def push(role, blocks):
            if out and out[-1]["role"] == role:
                out[-1]["content"].extend(blocks)
            else:
                out.append({"role": role, "content": list(blocks)})

        for m in self.messages:
            if m["role"] == "user":
                push("user", [{"type": "text", "text": str(m.get("content") or "")}])
            elif m["role"] == "assistant":
                blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                for call in m.get("toolCalls") or []:
                    blocks.append({"type": "tool_use", "id": call["id"], "name": call["function"]["name"],
                                   "input": json.loads(call["function"].get("arguments") or "{}")})
                if blocks:
                    push("assistant", blocks)
            elif m["role"] == "tool":
                push("user", [{"type": "tool_result", "tool_use_id": m["toolCallId"], "content": str(m.get("content", ""))}])
        return out

    def frontend_tools(self) -> list[dict]:
        """Tools the page declared: the agent may call them; the page runs them."""
        return [{"name": t["name"], "description": t.get("description", ""),
                 "input_schema": t.get("parameters") or {"type": "object"}} for t in self.tools]


def model_events(llm, system, messages, tools=None, message_id=None):
    """Map one model turn onto AG-UI events. Yields (event, None) pairs, then (None, done).

    Text becomes TEXT_MESSAGE_*; each tool call becomes TOOL_CALL_START, a
    TOOL_CALL_ARGS per streamed JSON fragment, and TOOL_CALL_END.
    """
    message_id = message_id or _id("msg")
    open_text = False
    for e in llm.stream(system, messages, tools):
        if e["type"] == "text":
            if not open_text:
                open_text = True
                yield text_start(message_id), None
            yield text_content(message_id, e["text"]), None
        elif e["type"] == "tool_start":
            if open_text:
                open_text = False
                yield text_end(message_id), None
            yield tool_start(e["id"], e["name"], message_id), None
        elif e["type"] == "tool_delta":
            yield tool_args(e["id"], e["json"]), None
        elif e["type"] == "tool_end":
            yield tool_end(e["id"]), None
        elif e["type"] == "done":
            if open_text:
                yield text_end(message_id), None
            yield None, e
