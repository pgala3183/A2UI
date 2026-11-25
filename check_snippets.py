"""Check that every code snippet quoted in a README exists in the file it names.

    python check_snippets.py            all READMEs
    python check_snippets.py codelabs/03_mcp_apps

A snippet is a ```python, ```js or ```html fence whose previous non-empty
line names a file in backticks, for example:  `server.py`:
Each snippet line (whitespace collapsed) must appear in that file. A line
that is just "..." marks an elision and is skipped. Paths are resolved from
the README's folder, then from the repository root.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FENCE = re.compile(r"^```(python|js|html)\s*$")
NAME = re.compile(r"`([\w./-]+\.(?:py|mjs|js|html))`")


def norm(line: str) -> str:
    return " ".join(line.split())


def check(readme: Path) -> list[str]:
    problems = []
    lines = readme.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        if FENCE.match(lines[i]):
            j = i + 1
            while j < len(lines) and lines[j].strip() != "```":
                j += 1
            before = next((lines[k] for k in range(i - 1, -1, -1) if lines[k].strip()), "")
            names = NAME.findall(before)
            if names:
                target = next((p for base in (readme.parent, ROOT) for p in [base / names[-1]] if p.is_file()), None)
                if target is None:
                    problems.append(f"{readme.relative_to(ROOT)}:{i + 1}: file {names[-1]} not found")
                else:
                    body = {norm(x) for x in target.read_text(encoding="utf-8").splitlines()}
                    for n, snippet_line in enumerate(lines[i + 1:j], start=i + 2):
                        s = norm(snippet_line)
                        if s and s != "..." and s not in body:
                            problems.append(f"{readme.relative_to(ROOT)}:{n}: not in {names[-1]}: {s[:80]}")
            i = j
        i += 1
    return problems


def main():
    args = sys.argv[1:]
    readmes = [p for p in ROOT.rglob("README.md") if not any(part.startswith(".") or part == "node_modules" for part in p.parts)
               and (not args or any(a.replace("\\", "/") in p.as_posix() for a in args))]
    problems = [problem for readme in sorted(readmes) for problem in check(readme)]
    print("\n".join(problems) if problems else f"all snippets found ({len(readmes)} READMEs checked)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
