"""add video_content_analyses table

Revision ID: d1e2f3a4b5c6
Revises: c7d8e9f0a1b2
Create Date: 2026-02-02 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'video_content_analyses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('competitor_video_id', sa.UUID(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('strengths', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('weaknesses', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['competitor_video_id'], ['competitor_videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('competitor_video_id'),
    )


def downgrade() -> None:
    op.drop_table('video_content_analyses')
