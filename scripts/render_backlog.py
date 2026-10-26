#!/usr/bin/env python3
"""Render backlog/backlog.json into backlog/tasks.md.

Usage:
  python3 scripts/render_backlog.py           # rewrite backlog/tasks.md
  python3 scripts/render_backlog.py --check   # exit 1 if tasks.md is out of date (for CI)

Standard library only. Run it after every change to backlog.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "backlog" / "backlog.json"
TASKS_MD = ROOT / "backlog" / "tasks.md"

ROLE_NAMES = {
    "lead": "Lead",
    "backend": "Backend agent",
    "frontend": "Frontend agent",
    "platform": "Platform agent",
    "test": "Test agent",
    "reviewer": "Reviewer agent",
}

HEADER = """# MediTrack — Backlog

Source of truth: [backlog.json](backlog.json). This page is generated from it. Import to GitHub with `scripts/create_backlog.py` (see the [main README](../README.md#project-board)).

Priorities: **P0** needed to pass, **P1** strongly recommended, **P2** later. Task IDs are stable; GitHub issue numbers are assigned on import.
"""


def render(tasks: list[dict]) -> str:
    lines = [HEADER, "| ID | Title | Owner | Pri | Depends on |", "|---|---|---|---|---|"]
    for t in tasks:
        deps = ", ".join(t["depends_on"]) or "—"
        lines.append(f"| {t['id']} | {t['title']} | {ROLE_NAMES[t['role']]} | {t['priority']} | {deps} |")
    for t in tasks:
        lines += [
            "",
            f"## {t['id']} — {t['title']}",
            "",
            f"- **Owner:** {ROLE_NAMES[t['role']]}  ·  **Priority:** {t['priority']}  ·  **Phase:** {t['phase']}",
            f"- **Depends on:** {', '.join(t['depends_on']) or 'none'}",
            f"- **Files:** {', '.join(f'`{f}`' for f in t['files'])}",
            "",
            "**Acceptance criteria**",
            "",
            *[f"- [ ] {a}" for a in t["acceptance"]],
            "",
            "**Verification**",
            "",
            "```bash",
            *t["verify"],
            "```",
        ]
        if t.get("notes"):
            lines += ["", f"**Notes:** {t['notes']}"]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Fail if tasks.md is out of date")
    args = parser.parse_args()
    tasks = json.loads(BACKLOG.read_text(encoding="utf-8"))["tasks"]
    ids = [t["id"] for t in tasks]
    known = set(ids)
    problems = [f"duplicate id {i}" for i in sorted(known) if ids.count(i) > 1]
    problems += [f"{t['id']} depends on unknown {d}" for t in tasks for d in t["depends_on"] if d not in known]
    problems += [f"{t['id']} has unknown role {t['role']}" for t in tasks if t["role"] not in ROLE_NAMES]
    if problems:
        print("backlog.json problems:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    text = render(tasks)
    if args.check:
        current = TASKS_MD.read_text(encoding="utf-8") if TASKS_MD.exists() else ""
        if current != text:
            print("backlog/tasks.md is out of date: run python3 scripts/render_backlog.py", file=sys.stderr)
            return 1
        print("backlog/tasks.md is up to date")
        return 0
    TASKS_MD.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {TASKS_MD.relative_to(ROOT)} ({len(tasks)} tasks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
