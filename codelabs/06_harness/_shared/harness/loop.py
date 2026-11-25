"""The agent loop, as a generator of events.

    {"type": "text", "text"}                       model prose, streamed
    {"type": "tool_call", "id", "name", "input"}   a call the model made
    {"type": "tool_result", "id", "name", "content", "is_error"}
    {"type": "ui", ...}                            generative UI from a tool (see each step)
    {"type": "permission_request", "id", "name", "input"}   the loop is paused
    {"type": "done", "reason"}

The harness owns the conversation (unlike AG-UI, where the client sends the
history each run). A paused loop resumes with ``resume(id, approve)``; a UI
action from a surface starts a new turn with ``ui_action(...)``, but only for
actions the current UI declared.
"""

from __future__ import annotations

import json


class Harness:
    def __init__(self, llm, system: str, registry, max_turns: int = 8):
        self.llm = llm
        self.system = system
        self.registry = registry
        self.max_turns = max_turns
        self.messages: list[dict] = []
        self.pending: dict | None = None  # a paused batch of tool calls
        self.approved: set[str] = set()
        self.allowed_actions: dict[str, set[str]] = {}  # view id -> action names the UI declared

    # -- entry points ---------------------------------------------------------
    def ask(self, text: str):
        if self.pending:
            yield {"type": "error", "message": "waiting for a permission decision"}
            return
        self.messages.append({"role": "user", "content": text})
        yield from self._loop()

    def ui_action(self, view: str, action: str, params: dict):
        """A click in a generated UI. Only actions that UI declared are accepted."""
        if action not in self.allowed_actions.get(view, set()):
            yield {"type": "error", "message": f"action {action!r} was not declared by view {view!r}"}
            return
        yield from self.ask(f"[ui action] {action} {json.dumps(params)} (from view {view})")

    def resume(self, request_id: str, approve: bool):
        if not self.pending or self.pending["calls"][self.pending["index"]]["id"] != request_id:
            yield {"type": "error", "message": "no such permission request"}
            return
        batch, self.pending = self.pending, None
        if approve:
            self.approved.add(request_id)
        else:
            call = batch["calls"][batch["index"]]
            content = json.dumps({"error": "the user denied this action"})
            yield {"type": "tool_result", "id": call["id"], "name": call["name"], "content": content, "is_error": True}
            batch["results"].append({"type": "tool_result", "tool_use_id": call["id"], "content": content, "is_error": True})
            batch["index"] += 1
        paused = yield from self._run_calls(batch["calls"], batch["index"], batch["results"], announced=request_id)
        if paused:
            return
        self.messages.append({"role": "user", "content": batch["results"]})
        yield from self._loop()

    # -- the loop -------------------------------------------------------------
    def _loop(self):
        for _ in range(self.max_turns):
            done = None
            for event in self.llm.stream(self.system, self.messages, self.registry.for_model()):
                if event["type"] == "text":
                    yield {"type": "text", "text": event["text"]}
                elif event["type"] == "done":
                    done = event
            self.messages.append({"role": "assistant", "content": done["content"]})
            calls = [b for b in done["content"] if b["type"] == "tool_use"]
            if not calls:
                yield {"type": "done", "reason": done.get("stop_reason", "end_turn")}
                return
            results: list[dict] = []
            paused = yield from self._run_calls(calls, 0, results)
            if paused:
                return
            self.messages.append({"role": "user", "content": results})
        yield {"type": "done", "reason": "max_turns"}

    def _run_calls(self, calls: list[dict], start: int, results: list[dict], announced: str | None = None):
        """Run calls[start:]. Returns True when the loop paused for permission."""
        for index in range(start, len(calls)):
            call = calls[index]
            tool = self.registry.get(call["name"])
            if call["id"] != announced:  # an approved call was already announced before the pause
                yield {"type": "tool_call", "id": call["id"], "name": call["name"], "input": call["input"]}
            if tool is None or tool.permission == "deny":
                content, events, is_error = json.dumps({"error": f"tool {call['name']} is not available"}), [], True
            elif tool.permission == "ask" and call["id"] not in self.approved:
                self.pending = {"calls": calls, "index": index, "results": results}
                yield {"type": "permission_request", "id": call["id"], "name": call["name"], "input": call["input"]}
                return True
            else:
                content, events, is_error = tool.execute(call["input"])
            for event in events:
                if event.get("actions") is not None:  # a UI declares which actions it may send back
                    self.allowed_actions[event["view"]] = set(event["actions"])
                yield event
            yield {"type": "tool_result", "id": call["id"], "name": call["name"], "content": content, "is_error": is_error}
            results.append({"type": "tool_result", "tool_use_id": call["id"], "content": content, "is_error": is_error})
        return False
