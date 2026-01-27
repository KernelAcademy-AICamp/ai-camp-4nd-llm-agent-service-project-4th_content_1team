"""Add YouTube channel related tables

Revision ID: 2026_01_26_0001
Revises: e9538178d61d
Create Date: 2026-01-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_01_26_0001"
down_revision: Union[str, None] = "e9538178d61d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "youtube_channels",
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("keywords", sa.String(), nullable=True),
        sa.Column("raw_channel_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("channel_id"),
    )

    op.create_table(
        "yt_channel_stats_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("subscriber_count", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.BigInteger(), nullable=True),
        sa.Column("video_count", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.Column("raw_stats_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["youtube_channels.channel_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "date", name="uq_stats_channel_date"),
    )
    op.create_index("ix_stats_channel_id", "yt_channel_stats_daily", ["channel_id"], unique=False)
    op.create_index("ix_stats_date", "yt_channel_stats_daily", ["date"], unique=False)

    op.create_table(
        "yt_channel_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("topic_category_url", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["youtube_channels.channel_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "topic_category_url", name="uq_topics_channel_topic"),
    )
    op.create_index("ix_topics_channel_id", "yt_channel_topics", ["channel_id"], unique=False)

    op.create_table(
        "yt_audience_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("age_group", sa.String(), nullable=False),
        sa.Column("gender", sa.String(), nullable=False),
        sa.Column("viewer_percentage", sa.Float(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("watch_time_minutes", sa.Float(), nullable=True),
        sa.Column("raw_report_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["youtube_channels.channel_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "date", "age_group", "gender", name="uq_audience_channel_date_age_gender"),
    )
    op.create_index("ix_audience_channel_id", "yt_audience_daily", ["channel_id"], unique=False)
    op.create_index("ix_audience_date", "yt_audience_daily", ["date"], unique=False)

    op.create_table(
        "yt_geo_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("viewer_percentage", sa.Float(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("watch_time_minutes", sa.Float(), nullable=True),
        sa.Column("raw_report_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["youtube_channels.channel_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "date", "country", name="uq_geo_channel_date_country"),
    )
    op.create_index("ix_geo_channel_id", "yt_geo_daily", ["channel_id"], unique=False)
    op.create_index("ix_geo_date", "yt_geo_daily", ["date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_geo_date", table_name="yt_geo_daily")
    op.drop_index("ix_geo_channel_id", table_name="yt_geo_daily")
    op.drop_table("yt_geo_daily")

    op.drop_index("ix_audience_date", table_name="yt_audience_daily")
    op.drop_index("ix_audience_channel_id", table_name="yt_audience_daily")
    op.drop_table("yt_audience_daily")

    op.drop_index("ix_topics_channel_id", table_name="yt_channel_topics")
    op.drop_table("yt_channel_topics")

    op.drop_index("ix_stats_date", table_name="yt_channel_stats_daily")
    op.drop_index("ix_stats_channel_id", table_name="yt_channel_stats_daily")
    op.drop_table("yt_channel_stats_daily")

    op.drop_table("youtube_channels")
