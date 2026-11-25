"""RFC 6901 JSON Pointer and the RFC 6902 operations generative UI needs.

A2UI addresses its data model with pointers, AG-UI sends STATE_DELTA as JSON
Patch, and json-render streams patches into its element map. One small,
careful implementation serves all three.

Safety rules: keys ``__proto__``, ``constructor`` and ``prototype`` are
refused (they matter in the JavaScript twin, and the rule is kept identical),
and list indices must be digits or ``-`` (append).
"""

from __future__ import annotations

import copy

FORBIDDEN = {"__proto__", "constructor", "prototype"}


class PatchError(ValueError):
    pass


def parse_pointer(pointer: str) -> list[str]:
    if pointer in ("", "/"):
        return []
    if not pointer.startswith("/"):
        raise PatchError(f"pointer must start with '/': {pointer!r}")
    tokens = [t.replace("~1", "/").replace("~0", "~") for t in pointer[1:].split("/")]
    for token in tokens:
        if token in FORBIDDEN:
            raise PatchError(f"forbidden key {token!r}")
    return tokens


def _index(container: list, token: str, allow_end: bool) -> int:
    if token == "-" and allow_end:
        return len(container)
    if not token.isdigit():
        raise PatchError(f"bad list index {token!r}")
    index = int(token)
    if index > len(container) or (index == len(container) and not allow_end):
        raise PatchError(f"index {index} out of range")
    return index


def get(doc, pointer: str, default=None):
    node = doc
    for token in parse_pointer(pointer):
        if isinstance(node, dict):
            if token not in node:
                return default
            node = node[token]
        elif isinstance(node, list):
            if not token.isdigit() or int(token) >= len(node):
                return default
            node = node[int(token)]
        else:
            return default
    return node


def _parent(doc, tokens: list[str], create: bool):
    node = doc
    for token in tokens[:-1]:
        if isinstance(node, dict):
            if token not in node:
                if not create:
                    raise PatchError(f"missing parent {token!r}")
                node[token] = {}
            node = node[token]
        elif isinstance(node, list):
            node = node[_index(node, token, False)]
        else:
            raise PatchError(f"cannot descend into {type(node).__name__}")
    return node


def set_value(doc, pointer: str, value, create: bool = True):
    """Set ``value`` at ``pointer`` (A2UI-style upsert). Returns the new document."""
    tokens = parse_pointer(pointer)
    if not tokens:
        return value
    parent = _parent(doc, tokens, create)
    last = tokens[-1]
    if isinstance(parent, list):
        index = _index(parent, last, True)
        if index == len(parent):
            parent.append(value)
        else:
            parent[index] = value
    else:
        parent[last] = value
    return doc


def remove(doc, pointer: str):
    tokens = parse_pointer(pointer)
    if not tokens:
        return None
    parent = _parent(doc, tokens, False)
    last = tokens[-1]
    if isinstance(parent, list):
        del parent[_index(parent, last, False)]
    elif last in parent:
        del parent[last]
    else:
        raise PatchError(f"nothing to remove at {pointer}")
    return doc


def apply_op(doc, op: dict):
    """Apply one RFC 6902 operation in place; returns the (possibly new) root."""
    kind, path = op.get("op"), op.get("path")
    if not isinstance(path, str):
        raise PatchError("operation needs a string 'path'")
    if kind == "add":
        tokens = parse_pointer(path)
        if not tokens:
            return copy.deepcopy(op["value"])
        parent = _parent(doc, tokens, False)
        if isinstance(parent, list):
            parent.insert(_index(parent, tokens[-1], True), copy.deepcopy(op["value"]))
        else:
            parent[tokens[-1]] = copy.deepcopy(op["value"])
        return doc
    if kind == "replace":
        if get(doc, path, _MISSING) is _MISSING:
            raise PatchError(f"nothing to replace at {path}")
        return set_value(doc, path, copy.deepcopy(op["value"]), create=False)
    if kind == "remove":
        return remove(doc, path)
    if kind == "test":
        if get(doc, path, _MISSING) != op.get("value"):
            raise PatchError(f"test failed at {path}")
        return doc
    raise PatchError(f"unsupported op {kind!r}")


def apply_patch(doc, ops: list[dict]):
    """Apply a list of operations to a copy; the input is left untouched."""
    result = copy.deepcopy(doc)
    for op in ops:
        result = apply_op(result, op)
    return result


def diff(old, new, path: str = "") -> list[dict]:
    """A small structural diff: the ops that turn ``old`` into ``new``.

    Dicts are compared key by key; anything else that differs is replaced.
    It is enough to turn two UI states into a STATE_DELTA.
    """
    if isinstance(old, dict) and isinstance(new, dict):
        ops = []
        for key in old:
            if key not in new:
                ops.append({"op": "remove", "path": f"{path}/{_escape(key)}"})
        for key, value in new.items():
            child = f"{path}/{_escape(key)}"
            if key not in old:
                ops.append({"op": "add", "path": child, "value": value})
            else:
                ops.extend(diff(old[key], value, child))
        return ops
    if old != new:
        return [{"op": "replace", "path": path or "", "value": new}]
    return []


def _escape(key: str) -> str:
    return str(key).replace("~", "~0").replace("/", "~1")


class _Missing:
    pass


_MISSING = _Missing()
