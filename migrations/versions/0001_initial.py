"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# Значения хранятся в lowercase (см. PgEnum / values_callable в моделях).
channel_enum = postgresql.ENUM("sms", "email", name="notificationchannel", create_type=False)
priority_enum = postgresql.ENUM("high", "normal", name="notificationpriority", create_type=False)
status_enum = postgresql.ENUM(
    "queued", "sent", "delivered", "dropped", name="notificationstatus", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    channel_enum.create(bind, checkfirst=True)
    priority_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    op.create_table(
        "subscribers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "subscriber_contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subscriber_id",
            sa.Integer(),
            sa.ForeignKey("subscribers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", channel_enum, nullable=False),
        sa.Column("contact", sa.String(length=255), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_subscriber_contacts_sub_channel",
        "subscriber_contacts",
        ["subscriber_id", "channel"],
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("subscriber_id", sa.BigInteger(), nullable=False),
        sa.Column("channel", channel_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("priority", priority_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("provider_response", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_notifications_idempotency_key"),
    )
    op.create_index(
        "ix_notifications_status_retry", "notifications", ["status", "next_retry_at"]
    )
    op.create_index(
        "ix_notifications_subscriber_created", "notifications", ["subscriber_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_subscriber_created", table_name="notifications")
    op.drop_index("ix_notifications_status_retry", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_subscriber_contacts_sub_channel", table_name="subscriber_contacts")
    op.drop_table("subscriber_contacts")
    op.drop_table("subscribers")

    bind = op.get_bind()
    status_enum.drop(bind, checkfirst=True)
    priority_enum.drop(bind, checkfirst=True)
    channel_enum.drop(bind, checkfirst=True)
