"""add recent_video_comments table

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-02-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f6g7h8i9j0k1'
down_revision = 'e5f6g7h8i9j0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'recent_video_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('recent_video_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('competitor_recent_videos.id', ondelete='CASCADE'), nullable=False),

        # 댓글 정보
        sa.Column('comment_id', sa.String(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('author_name', sa.String(), nullable=True),
        sa.Column('author_thumbnail', sa.Text(), nullable=True),
        sa.Column('likes', sa.Integer(), default=0),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),

        # 메타
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # 인덱스
    op.create_index('ix_recent_video_comments_recent_video_id',
                    'recent_video_comments', ['recent_video_id'])


def downgrade() -> None:
    op.drop_index('ix_recent_video_comments_recent_video_id', 'recent_video_comments')
    op.drop_table('recent_video_comments')
