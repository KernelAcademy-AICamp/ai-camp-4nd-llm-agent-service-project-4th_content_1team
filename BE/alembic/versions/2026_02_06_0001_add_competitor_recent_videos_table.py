"""add competitor_recent_videos table

Revision ID: e5f6g7h8i9j0
Revises: b2c3d4e5f6g8
Create Date: 2026-02-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e5f6g7h8i9j0'
down_revision = 'b2c3d4e5f6g8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'competitor_recent_videos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('competitor_channel_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('competitor_channels.id', ondelete='CASCADE'), nullable=False),

        # YouTube 영상 정보
        sa.Column('video_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration', sa.String(), nullable=True),

        # 통계
        sa.Column('view_count', sa.Integer(), default=0),
        sa.Column('like_count', sa.Integer(), default=0),
        sa.Column('comment_count', sa.Integer(), default=0),

        # AI 분석 결과
        sa.Column('analysis_summary', sa.Text(), nullable=True),
        sa.Column('analysis_strengths', postgresql.JSONB(), nullable=True),
        sa.Column('analysis_weaknesses', postgresql.JSONB(), nullable=True),
        sa.Column('audience_reaction', sa.Text(), nullable=True),

        # 메타
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 인덱스
    op.create_index('ix_competitor_recent_videos_competitor_channel_id',
                    'competitor_recent_videos', ['competitor_channel_id'])
    op.create_index('ix_competitor_recent_videos_video_id',
                    'competitor_recent_videos', ['video_id'])


def downgrade() -> None:
    op.drop_index('ix_competitor_recent_videos_video_id', 'competitor_recent_videos')
    op.drop_index('ix_competitor_recent_videos_competitor_channel_id', 'competitor_recent_videos')
    op.drop_table('competitor_recent_videos')
