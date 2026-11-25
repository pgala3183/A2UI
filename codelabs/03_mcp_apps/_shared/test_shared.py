"""Tests for the MCP Apps theme's shared plumbing."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[2] / "common"), str(HERE)]

import mcp_app  # noqa: E402


def test_load_view_inlines_the_kit(tmp_path):
    view = tmp_path / "view.html"
    view.write_text("<html><head><!--VIEW_KIT--></head><body></body></html>", encoding="utf-8")
    html = mcp_app.load_view(view)
    assert "<!--VIEW_KIT-->" not in html and "window.viewKit" in html and "ui/initialize" in html


def test_view_meta_denies_all_network_by_default():
    assert mcp_app.VIEW_META["ui"]["csp"] == {"connectDomains": [], "resourceDomains": []}
    assert mcp_app.MIME == "text/html;profile=mcp-app"


def test_host_files_exist_and_speak_the_bridge():
    host = (HERE / "host" / "host.mjs").read_text(encoding="utf-8")
    for method in ("ui/initialize", "ui/notifications/tool-input", "ui/notifications/tool-result",
                   "tools/call", "ui/message", "ui/open-link", "ui/update-model-context"):
        assert method in host, method
    assert "sandbox: 'allow-scripts'" in host and "allow-same-origin" not in host
