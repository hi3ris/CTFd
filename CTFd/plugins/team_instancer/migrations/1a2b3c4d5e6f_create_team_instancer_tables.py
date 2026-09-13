"""Create team instancer tables

Revision ID: 1a2b3c4d5e6f
Revises:
Create Date: 2026-09-10

Runs only on non-SQLite databases (SQLite uses create_all). Creates the
polymorphic challenge subtable and the two bookkeeping tables. Guarded so a
re-run on an existing DB does not fail.
"""

import sqlalchemy as sa

revision = "1a2b3c4d5e6f"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(op, name):
    insp = sa.inspect(op.get_bind())
    return name in insp.get_table_names()


def upgrade(op=None):
    if not _has_table(op, "team_instance_challenge"):
        op.create_table(
            "team_instance_challenge",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("initial", sa.Integer(), nullable=True),
            sa.Column("minimum", sa.Integer(), nullable=True),
            sa.Column("decay", sa.Integer(), nullable=True),
            sa.Column("function", sa.String(length=32), nullable=True),
            sa.Column("docker_image", sa.String(length=160), nullable=True),
            sa.Column("internal_port", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["id"], ["challenges.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(op, "team_instance"):
        op.create_table(
            "team_instance",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("challenge_id", sa.Integer(), nullable=False),
            sa.Column("container_id", sa.String(length=64), nullable=True),
            sa.Column("port", sa.Integer(), nullable=True),
            sa.Column("network_name", sa.String(length=128), nullable=True),
            sa.Column("proxy_name", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("start_time", sa.DateTime(), nullable=True),
            sa.Column("renew_count", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("account_id", "challenge_id", name="uq_team_challenge"),
        )
        op.create_index("ix_team_instance_account_id", "team_instance", ["account_id"])

    if not _has_table(op, "frp_port"):
        op.create_table(
            "frp_port",
            sa.Column("port", sa.Integer(), nullable=False),
            sa.Column("instance_id", sa.Integer(), nullable=True),
            sa.Column("account_id", sa.Integer(), nullable=True),
            sa.Column("challenge_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["instance_id"], ["team_instance.id"]),
            sa.PrimaryKeyConstraint("port"),
        )


def downgrade(op=None):
    for t in ("frp_port", "team_instance", "team_instance_challenge"):
        try:
            op.drop_table(t)
        except Exception:
            pass
