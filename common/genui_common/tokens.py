"""Count tokens so the modes can be compared on cost.

Uses tiktoken's ``o200k_base`` encoding when it is installed and its data is
available. Otherwise it falls back to ``ceil(chars / 4)`` and says so. The
numbers compare *representations* of the same UI; they are not Claude's own
token counts (use the API's ``count_tokens`` endpoint for those).
"""

from __future__ import annotations

import math

_ENCODER = None
_LABEL = None


def _encoder():
    global _ENCODER, _LABEL
    if _LABEL is None:
        try:
            import tiktoken

            _ENCODER = tiktoken.get_encoding("o200k_base")
            _LABEL = "tiktoken o200k_base"
        except Exception:  # not installed, or no network to fetch the encoding
            _ENCODER, _LABEL = None, "estimate: chars/4"
    return _ENCODER


def count(text: str) -> int:
    encoder = _encoder()
    if encoder is None:
        return math.ceil(len(text) / 4)
    return len(encoder.encode(text))


def method() -> str:
    _encoder()
    return _LABEL
