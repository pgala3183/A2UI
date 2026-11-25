"""A custom A2UI component for model-written HTML: ``HtmlFrame``.

A2UI keeps catalogs swappable: ``createSurface`` names a ``catalogId`` and
the client renders only what that catalog defines. The Basic Catalog has no
way to run arbitrary code, on purpose. These two catalogs add one component
that does, under rules the application enforces:

* the server checks the HTML against a content policy before forwarding it;
* the client renders it in ``<iframe sandbox="allow-scripts">`` with a CSP;
* the frame sees the surface's data model and can only send named actions.

``OPEN_CATALOG`` has HtmlFrame alone (open-ended mode). ``MIXED_CATALOG`` is
the Basic Catalog plus HtmlFrame (mixed mode).
"""

from __future__ import annotations

import a2ui
from genui_common.sandbox import check_html

HTML_FRAME = ("An interactive HTML document (inline CSS and JS only, no network). It runs in a sandboxed "
              "iframe; it reads the surface's data model with genui.onData(fn) and sends actions with "
              "genui.send(name, payload).",
              {"html": {"type": "string", "minLength": 20}, "title": {"type": "string"},
               "height": {"type": "number", "minimum": 80, "maximum": 1200}}, ["html"])


def policy(component: dict) -> list[str]:
    return [f"html: {problem}" for problem in check_html(component.get("html", ""))]


OPEN_CATALOG = a2ui.Catalog("genux.dev:bikes/open-ended/v1", {"HtmlFrame": HTML_FRAME}, {"HtmlFrame": policy})
MIXED_CATALOG = a2ui.Catalog("genux.dev:bikes/mixed/v1", {**a2ui.BASIC, "HtmlFrame": HTML_FRAME}, {"HtmlFrame": policy})
