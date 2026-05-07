"""lowercase_enum_values

Switch enum-typed columns from storing the Python enum NAME (e.g. 'PLUMBING')
to storing its VALUE (e.g. 'plumbing'). The model now uses
``values_callable=...``; this migration backfills any pre-existing rows so
SQLAlchemy can deserialize them.

Revision ID: b3dd13738834
Revises: f2290511537e
Create Date: 2026-05-07 20:30:50.665096
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b3dd13738834"
down_revision: Union[str, None] = "f2290511537e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column) pairs whose stored values must be re-cased.
_ENUM_COLUMNS: tuple[tuple[str, str], ...] = (
    ("complaints", "category"),
    ("complaints", "urgency"),
    ("ledger", "status"),
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Native PG enum: rename each label in place. Postgres preserves the
        # numeric ordinal, so existing rows continue to point at the same value.
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'PLUMBING' TO 'plumbing'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'ELECTRICAL' TO 'electrical'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'CLEANING' TO 'cleaning'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'APPLIANCE' TO 'appliance'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'SECURITY' TO 'security'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'INTERNET' TO 'internet'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'OTHER' TO 'other'")
        op.execute("ALTER TYPE complaint_urgency RENAME VALUE 'LOW' TO 'low'")
        op.execute("ALTER TYPE complaint_urgency RENAME VALUE 'MEDIUM' TO 'medium'")
        op.execute("ALTER TYPE complaint_urgency RENAME VALUE 'HIGH' TO 'high'")
        op.execute("ALTER TYPE ledger_status RENAME VALUE 'PENDING' TO 'pending'")
        op.execute("ALTER TYPE ledger_status RENAME VALUE 'PARTIAL' TO 'partial'")
        op.execute("ALTER TYPE ledger_status RENAME VALUE 'PAID' TO 'paid'")
        return

    # SQLite (and other dialects without native enums): the column is a plain
    # string with at most a CHECK constraint listing valid values. Lowercase
    # the existing data in place — the new constraint shape is already
    # captured by the baseline migration.
    for table, column in _ENUM_COLUMNS:
        op.execute(f"UPDATE {table} SET {column} = lower({column})")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'plumbing' TO 'PLUMBING'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'electrical' TO 'ELECTRICAL'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'cleaning' TO 'CLEANING'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'appliance' TO 'APPLIANCE'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'security' TO 'SECURITY'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'internet' TO 'INTERNET'")
        op.execute("ALTER TYPE complaint_category RENAME VALUE 'other' TO 'OTHER'")
        op.execute("ALTER TYPE complaint_urgency RENAME VALUE 'low' TO 'LOW'")
        op.execute("ALTER TYPE complaint_urgency RENAME VALUE 'medium' TO 'MEDIUM'")
        op.execute("ALTER TYPE complaint_urgency RENAME VALUE 'high' TO 'HIGH'")
        op.execute("ALTER TYPE ledger_status RENAME VALUE 'pending' TO 'PENDING'")
        op.execute("ALTER TYPE ledger_status RENAME VALUE 'partial' TO 'PARTIAL'")
        op.execute("ALTER TYPE ledger_status RENAME VALUE 'paid' TO 'PAID'")
        return

    for table, column in _ENUM_COLUMNS:
        op.execute(f"UPDATE {table} SET {column} = upper({column})")
