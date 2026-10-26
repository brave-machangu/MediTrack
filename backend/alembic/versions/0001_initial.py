"""Create patients, medications, schedules and dose_logs (backend/DESIGN.md §2).

Revision ID: 0001
Revises:
Create Date: 2026-10-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # CHECK names are wrapped in op.f(): Alembic applies the models' naming convention
    # ("ck_%(table_name)s_%(constraint_name)s") to operations too, so a plain name would come
    # out as "ck_schedules_ck_schedules_...". The other conventions don't reuse the name.
    op.create_table(
        "patients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_patients"),
    )
    op.create_table(
        "medications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("dosage_label", sa.String(100), nullable=False),
        sa.Column("instructions", sa.String(500), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_medications_patient_id_patients",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_medications"),
    )
    op.create_index("ix_medications_patient_id", "medications", ["patient_id"])
    op.create_table(
        "schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("medication_id", sa.Uuid(), nullable=False),
        sa.Column("times_of_day", sa.JSON(), nullable=False),
        sa.Column("days_of_week", sa.JSON(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("grace_period_minutes", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name=op.f("ck_schedules_end_after_start")
        ),
        sa.CheckConstraint(
            "grace_period_minutes BETWEEN 0 AND 240", name=op.f("ck_schedules_grace_range")
        ),
        sa.ForeignKeyConstraint(
            ["medication_id"],
            ["medications.id"],
            name="fk_schedules_medication_id_medications",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_schedules"),
    )
    op.create_index("ix_schedules_medication_id", "schedules", ["medication_id"])
    op.create_table(
        "dose_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(7), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("late", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(280), nullable=True),
        sa.CheckConstraint("status IN ('taken', 'skipped')", name=op.f("ck_dose_logs_status")),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["schedules.id"],
            name="fk_dose_logs_schedule_id_schedules",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dose_logs"),
        sa.UniqueConstraint("schedule_id", "scheduled_for", name="uq_dose_log_schedule_time"),
    )


def downgrade() -> None:
    op.drop_table("dose_logs")
    op.drop_index("ix_schedules_medication_id", table_name="schedules")
    op.drop_table("schedules")
    op.drop_index("ix_medications_patient_id", table_name="medications")
    op.drop_table("medications")
    op.drop_table("patients")
