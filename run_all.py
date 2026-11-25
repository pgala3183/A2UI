"""Run every test, and optionally every demo, in this repository.

    python run_all.py                       all offline tests, one pytest process per directory
    python run_all.py codelabs/02_ag_ui     only paths that contain this text
    python run_all.py --demos               also run each codelab's demo.py, save demo_output.txt
                                            and paste the output into the codelab README

Each directory runs in its own process because the codelabs reuse module
names (server.py, agent.py) on purpose: each one reads on its own.
A skipped test is reported as skipped, never as passed.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START, END = "<!-- demo-output:start -->", "<!-- demo-output:end -->"
MAX_README_LINES = 70


def test_dirs() -> list[Path]:
    dirs = [ROOT / "common" / "tests"]
    for theme in sorted((ROOT / "codelabs").iterdir()):
        if theme.is_dir():
            dirs += [d for d in sorted(theme.iterdir()) if d.is_dir() and list(d.glob("test_*.py"))]
    return dirs


def env(**extra) -> dict:
    e = dict(os.environ, PYTHONIOENCODING="utf-8", GENUI_TERMINAL_MIRROR="0", **extra)
    e.pop("GENUI_LIVE", None)  # tests and recorded demos never call a paid model
    return e


def run_tests(directory: Path) -> tuple[str, str]:
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=directory,
                            capture_output=True, text=True, env=env(GENUI_DELAY="0"), timeout=600)
    summary = (result.stdout.strip().splitlines() or ["(no output)"])[-1]
    return ("ok" if result.returncode == 0 else "FAIL"), summary + ("" if result.returncode == 0 else "\n" + result.stdout[-3000:])


def run_demo(directory: Path) -> tuple[bool, str, float]:
    started = time.time()
    result = subprocess.run([sys.executable, "demo.py"], cwd=directory, capture_output=True, text=True,
                            env=env(), timeout=600, encoding="utf-8")
    output = result.stdout + (f"\n[stderr]\n{result.stderr[-2000:]}" if result.returncode else "")
    return result.returncode == 0, output, time.time() - started


def paste_output(readme: Path, output: str):
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    if START not in text:
        return
    lines = output.rstrip().splitlines()
    if len(lines) > MAX_README_LINES:
        lines = lines[:MAX_README_LINES] + [f"... ({len(lines) - MAX_README_LINES} more lines in demo_output.txt)"]
    block = f"{START}\n```text\n" + "\n".join(lines) + f"\n```\n{END}"
    readme.write_text(re.sub(re.escape(START) + ".*?" + re.escape(END), lambda m: block, text, flags=re.S), encoding="utf-8")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    demos = "--demos" in sys.argv
    dirs = [d for d in test_dirs() if not args or any(a.replace("\\", "/") in d.as_posix() for a in args)]
    failures = 0
    print(f"{'directory':<44} {'tests':<6} summary")
    for directory in dirs:
        status, summary = run_tests(directory)
        failures += status != "ok"
        print(f"{directory.relative_to(ROOT).as_posix():<44} {status:<6} {summary}", flush=True)
    if demos:
        print(f"\n{'codelab':<44} {'demo':<6} seconds")
        for directory in dirs:
            if not (directory / "demo.py").exists():
                continue
            ok, output, seconds = run_demo(directory)
            failures += not ok
            (directory / "demo_output.txt").write_text(output, encoding="utf-8")
            paste_output(directory / "README.md", output)
            print(f"{directory.relative_to(ROOT).as_posix():<44} {'ok' if ok else 'FAIL':<6} {seconds:.1f}", flush=True)
    print("\nall green" if not failures else f"\n{failures} failing")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
