"""Helpers for the ``demo.py`` script in every codelab.

A demo prints what happens on the wire, then (when Playwright and Chromium
are installed) opens the page headlessly, clicks through it and saves
screenshots next to the script. Without Playwright it still prints the
wire-level transcript and says that the screenshot step was skipped.
"""

from __future__ import annotations

import json
import os
import textwrap
from contextlib import contextmanager
from pathlib import Path


def post_sse(url: str, body: dict, timeout: float = 60) -> list[tuple[str | None, object]]:
    """POST a JSON body and read the whole SSE response as (event, data) pairs."""
    import urllib.request

    from .sse import parse

    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Accept": "text/event-stream"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return parse(response.read().decode("utf-8"))


def post_json(url: str, body: dict, timeout: float = 60):
    import urllib.request

    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def section(title: str):
    print(f"\n=== {title} ===", flush=True)


def show(obj, limit: int = 160):
    """Print one JSON value on one line, cut to ``limit`` characters."""
    text = obj if isinstance(obj, str) else json.dumps(obj, separators=(",", ":"))
    print("  " + (text if len(text) <= limit else text[:limit - 3] + "..."), flush=True)


def wrap(text: str, width: int = 100, indent: str = "  "):
    for line in text.splitlines() or [""]:
        print(textwrap.fill(line, width, initial_indent=indent, subsequent_indent=indent) if line else "", flush=True)


@contextmanager
def browser(width: int = 1280, height: int = 860):
    """Yield a Playwright page, or None when Playwright/Chromium is unavailable."""
    if os.environ.get("GENUI_NO_BROWSER"):
        yield None
        return
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  (playwright not installed: screenshot step skipped)")
        yield None
        return
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as error:  # Chromium not downloaded
            print(f"  (chromium unavailable: {str(error).splitlines()[0]}; screenshot step skipped)")
            yield None
            return
        page = b.new_page(viewport={"width": width, "height": height})
        messages = []
        page.on("console", lambda m: messages.append(f"{m.type}: {m.text}"))
        page.console_messages = messages
        try:
            yield page
        finally:
            b.close()


def screenshot(page, path: Path | str, full_page: bool = True):
    # Chromium does not paint an iframe that lies below the viewport in a full-page
    # capture, so grow the viewport to the page's height first, then restore it.
    size = page.viewport_size
    height = page.evaluate("document.documentElement.scrollHeight")
    if full_page and size and height > size["height"]:
        page.set_viewport_size({"width": size["width"], "height": min(height, 4000)})
        page.wait_for_timeout(400)
    page.screenshot(path=str(path), full_page=full_page)
    if size:
        page.set_viewport_size(size)
    print(f"  saved {Path(path).name}", flush=True)


def frame_text(page, selector: str = "iframe") -> str:
    """Text inside the first sandboxed iframe matching ``selector``."""
    handle = page.query_selector(selector)
    frame = handle.content_frame() if handle else None
    return frame.inner_text("body") if frame else ""
