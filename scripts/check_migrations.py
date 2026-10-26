#!/usr/bin/env python3
"""Fail when a pull request adds a destructive Alembic migration without approval.

Migrations follow expand/contract (ADR-008, docs/operations.md §5.1): release N-1 must keep
working on release N's schema, so rollback never needs a down-migration. In a migration's
upgrade(), these operations break that rule unless the PR carries the `contract-migration` label
(Lead approval):

  drop_column, drop_table, rename_table, and alter_column(..., nullable=False | new_column_name= | type_=)

Only upgrade() is checked; downgrade() is expected to undo what upgrade() added.

Usage:
  python3 scripts/check_migrations.py --base origin/main --labels "label-a,label-b"   # CI
  python3 scripts/check_migrations.py --files path/to/migration.py ...                 # local check

Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = "backend/alembic/versions"
APPROVAL_LABEL = "contract-migration"
DESTRUCTIVE_CALLS = {"drop_column", "drop_table", "rename_table"}
DESTRUCTIVE_ALTER_KEYWORDS = {"new_column_name", "type_"}


def changed_migrations(base: str) -> list[Path]:
    """Migration files added or modified on this branch since it left `base`."""
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD", "--", MIGRATIONS_DIR],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [ROOT / line for line in out.splitlines() if line.endswith(".py")]


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def destructive_operations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    upgrades = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "upgrade"]
    findings = []
    for upgrade in upgrades:
        for node in ast.walk(upgrade):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            name = node.func.attr
            if name in DESTRUCTIVE_CALLS:
                findings.append(f"{_display(path)}:{node.lineno}: {name}()")
            elif name == "alter_column":
                for keyword in node.keywords:
                    makes_not_null = (
                        keyword.arg == "nullable"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is False
                    )
                    if makes_not_null or keyword.arg in DESTRUCTIVE_ALTER_KEYWORDS:
                        findings.append(f"{_display(path)}:{node.lineno}: alter_column({keyword.arg}=...)")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--base", help="Git ref the branch is compared with, e.g. origin/main")
    source.add_argument("--files", nargs="+", type=Path, help="Check these migration files instead")
    parser.add_argument("--labels", default="", help="Comma-separated labels on the pull request")
    args = parser.parse_args()

    files = [path.resolve() for path in args.files] if args.files else changed_migrations(args.base)
    findings = [finding for path in files for finding in destructive_operations(path)]
    print(f"checked {len(files)} migration file(s)")
    if not findings:
        print("OK: no destructive operations in upgrade()")
        return 0
    print("Destructive operations in upgrade():")
    for finding in findings:
        print(f"  - {finding}")
    labels = {label.strip() for label in args.labels.split(",") if label.strip()}
    if APPROVAL_LABEL in labels:
        print(f"Allowed: the PR has the '{APPROVAL_LABEL}' label (Lead-approved contract migration).")
        return 0
    print(f"FAIL: split this into expand and contract releases, or ask the Lead for the '{APPROVAL_LABEL}' label.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
