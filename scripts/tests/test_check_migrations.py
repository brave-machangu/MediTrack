"""Self-test for scripts/check_migrations.py. CI runs it before any migration exists.

Run: python -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "check_migrations.py"

EXPAND = """
    from alembic import op
    import sqlalchemy as sa

    def upgrade():
        op.add_column("patients", sa.Column("nickname", sa.String(40), nullable=True))
        op.alter_column("patients", "nickname", nullable=True)

    def downgrade():
        op.drop_column("patients", "nickname")
"""

CONTRACT = """
    from alembic import op
    import sqlalchemy as sa

    def upgrade():
        with op.batch_alter_table("patients") as batch_op:
            batch_op.drop_column("nickname")
            batch_op.alter_column("display_name", existing_type=sa.String(80), nullable=False)
        op.alter_column("medications", "name", new_column_name="label")
        op.alter_column("medications", "dose", type_=sa.Text())
        op.rename_table("dose_logs", "intake_logs")
        op.drop_table("legacy")

    def downgrade():
        pass
"""


def run(source: str, *extra: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        migration = Path(tmp) / "0001_example.py"
        migration.write_text(textwrap.dedent(source), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--files", str(migration), *extra],
            capture_output=True, text=True, check=False,
        )


class CheckMigrationsTest(unittest.TestCase):
    def test_expand_only_migration_passes(self) -> None:
        result = run(EXPAND)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("OK", result.stdout)

    def test_destructive_migration_fails_without_label(self) -> None:
        result = run(CONTRACT, "--labels", "backend,docs")
        self.assertEqual(result.returncode, 1, result.stdout)
        for operation in (
            "drop_column()",
            "alter_column(nullable=...)",
            "alter_column(new_column_name=...)",
            "alter_column(type_=...)",
            "rename_table()",
            "drop_table()",
        ):
            self.assertIn(operation, result.stdout)

    def test_destructive_migration_passes_with_label(self) -> None:
        result = run(CONTRACT, "--labels", "backend, contract-migration")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Allowed", result.stdout)


if __name__ == "__main__":
    unittest.main()


class DeliberateFailureDemo(unittest.TestCase):
    """MT-031 verification only (draft PR, never merged): CI must fail on this."""

    def test_deliberately_fails(self) -> None:
        self.assertEqual(1 + 1, 3, "deliberate failure for the MT-031 CI demo")
