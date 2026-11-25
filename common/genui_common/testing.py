"""Test helpers: run a codelab's Node tests from pytest.

Browser modules are plain ES modules. ``node --test`` runs their unit tests
with ``common/web/register.mjs`` loaded, which maps the URL paths the pages
use (``/common/...``, ``/shared/...``) onto files. When Node is not on PATH
the test is skipped, and a skip is reported as a skip, not as a pass.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REGISTER = Path(__file__).resolve().parent.parent / "web" / "register.mjs"


def run_node_tests(*files: Path | str) -> str:
    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not on PATH")
    cmd = [node, "--import", REGISTER.as_uri(), "--test", *[str(f) for f in files]]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    return output
