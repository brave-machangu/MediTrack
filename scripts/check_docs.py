#!/usr/bin/env python3
"""Check the specification for broken links and dangling references.

Checks every Markdown file in the repository:
  - relative links point to files that exist, and #anchors to headings that exist
  - every FR/NFR, AC, OPS and MT ID mentioned anywhere is defined
    (FR/NFR in docs/requirements.md, AC in docs/acceptance-criteria.md,
     OPS in docs/operations.md, MT in backlog/backlog.json)

Usage:
  python3 scripts/check_docs.py      # exit 1 and list problems if anything is broken

Standard library only. CI runs it on every PR (MT-031).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".claude", "node_modules", ".venv", "dist", "build"}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"```.*?```", re.S)


def markdown_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if not SKIP_DIRS.intersection(p.relative_to(ROOT).parts))


def slug(heading: str) -> str:
    """GitHub-style heading anchor."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    counts: dict[str, int] = {}
    in_code = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        match = None if in_code else re.match(r"^#{1,6}\s+(.*)$", line)
        if match:
            base = slug(match.group(1))
            n = counts.get(base, 0)
            found.add(base if n == 0 else f"{base}-{n}")
            counts[base] = n + 1
    return found


def check_links(files: list[Path]) -> list[str]:
    problems = []
    cache: dict[Path, set[str]] = {}
    for md in files:
        text = FENCE.sub("", md.read_text(encoding="utf-8"))
        for target in LINK.findall(text):
            if re.match(r"^(https?:|mailto:)", target):
                continue
            path_part, _, fragment = target.partition("#")
            dest = md if not path_part else (md.parent / path_part).resolve()
            rel = md.relative_to(ROOT)
            if not dest.exists():
                problems.append(f"{rel}: link to missing file: {target}")
            elif fragment and dest.suffix == ".md":
                if dest not in cache:
                    cache[dest] = anchors(dest)
                if fragment not in cache[dest]:
                    problems.append(f"{rel}: link to missing heading: {target}")
    return problems


def check_ids(files: list[Path]) -> list[str]:
    def read(rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    backlog = json.loads(read("backlog/backlog.json"))
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in files) + json.dumps(backlog)
    corpus += read("api/openapi.yaml")
    defined = {
        "AC": set(re.findall(r"^\| (AC-\d+) \|", read("docs/acceptance-criteria.md"), re.M)),
        "OPS": set(re.findall(r"^\| (OPS-\d+) \|", read("docs/operations.md"), re.M)),
        "MT": {t["id"] for t in backlog["tasks"]},
        "REQ": set(re.findall(r"^\| ((?:FR|NFR)-\d+)\b", read("docs/requirements.md"), re.M)),
    }
    patterns = {"AC": r"\bAC-\d+\b", "OPS": r"\bOPS-\d+\b", "MT": r"\bMT-\d{3}\b", "REQ": r"\b(?:FR|NFR)-\d+\b"}
    problems = []
    for kind, pattern in patterns.items():
        for ref in sorted(set(re.findall(pattern, corpus)) - defined[kind]):
            problems.append(f"{ref} is referenced but not defined")
    return problems


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    files = markdown_files()
    problems = check_links(files) + check_ids(files)
    print(f"checked {len(files)} Markdown files")
    for problem in problems:
        print(f"  - {problem}")
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
