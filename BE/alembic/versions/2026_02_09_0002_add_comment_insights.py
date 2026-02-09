"""add comment_insights column

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-02-09 00:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'h8i9j0k1l2m3'
down_revision = 'g7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'competitor_recent_videos',
        sa.Column('comment_insights', postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('competitor_recent_videos', 'comment_insights')
