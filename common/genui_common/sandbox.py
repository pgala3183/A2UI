"""Rules for model-written HTML (open-ended and mixed modes).

Two layers, both cheap:

1. ``check_html`` is a content policy applied on the server before the HTML is
   sent anywhere. It rejects network access, external code and storage. A
   violation is returned to the model as an error, like any validation error.
2. ``inject_csp`` puts a Content-Security-Policy ``<meta>`` first in the head.
   The browser then enforces "no network, inline code only" inside the
   sandboxed iframe, even if the policy check missed something.

The page adds the third layer: ``<iframe sandbox="allow-scripts">`` without
``allow-same-origin``, so the document gets an opaque origin and cannot reach
the page, its cookies or its storage. A sandbox reduces capabilities. It does
not make arbitrary model output trustworthy.
"""

from __future__ import annotations

import re

CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
       "img-src data:; font-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'")
MAX_BYTES = 60_000

POLICY = [
    (re.compile(r"<script[^>]*\ssrc\s*=", re.I), "external <script src> is not allowed"),
    (re.compile(r"<link[^>]*href\s*=\s*['\"]?(https?:)?//", re.I), "external stylesheet is not allowed"),
    (re.compile(r"\bfetch\s*\(", re.I), "network access (fetch) is not allowed"),
    (re.compile(r"XMLHttpRequest|WebSocket|EventSource|sendBeacon", re.I), "network access is not allowed"),
    (re.compile(r"document\.cookie|localStorage|sessionStorage|indexedDB", re.I), "storage access is not allowed"),
    (re.compile(r"<iframe|<object|<embed", re.I), "nested frames and plugins are not allowed"),
    (re.compile(r"<form[^>]*\saction\s*=", re.I), "form submission is not allowed"),
    (re.compile(r"\b(top|parent)\.location", re.I), "navigating the host page is not allowed"),
    (re.compile(r"https?://(?!www\.w3\.org/2000/svg)", re.I), "external URLs are not allowed"),
]


def check_html(html: str) -> list[str]:
    """Return the policy violations in ``html`` (empty list means it passes)."""
    problems = []
    if len(html.encode("utf-8")) > MAX_BYTES:
        problems.append(f"document is larger than {MAX_BYTES} bytes")
    for pattern, message in POLICY:
        if pattern.search(html) and message not in problems:
            problems.append(message)
    return problems


def inject_csp(html: str, csp: str = CSP) -> str:
    """Return ``html`` with a CSP meta tag as the first element of <head>."""
    meta = f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
    head = re.search(r"<head[^>]*>", html, re.I)
    if head:
        return html[:head.end()] + meta + html[head.end():]
    html_tag = re.search(r"<html[^>]*>", html, re.I)
    if html_tag:
        return html[:html_tag.end()] + "<head>" + meta + "</head>" + html[html_tag.end():]
    return "<!doctype html><html><head>" + meta + "</head><body>" + html + "</body></html>"
