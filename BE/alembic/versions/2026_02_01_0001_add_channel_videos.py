"""add yt_channel_videos and yt_video_stats tables

채널 영상 메타데이터 및 성과 통계 테이블 추가.
페르소나 생성을 위한 채널 영상 분석에 사용됩니다.

Revision ID: a1b2c3d4e5f6
Revises: f3ada8968c4b
Create Date: 2026-02-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f3ada8968c4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. yt_channel_videos 테이블 생성
    op.create_table(
        'yt_channel_videos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.String(), sa.ForeignKey('youtube_channels.channel_id', ondelete='CASCADE'), nullable=False),
        sa.Column('video_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('thumbnail_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # yt_channel_videos 인덱스
    op.create_unique_constraint('uq_channel_video', 'yt_channel_videos', ['channel_id', 'video_id'])
    op.create_index('ix_channel_videos_channel_id', 'yt_channel_videos', ['channel_id'])
    op.create_index('ix_channel_videos_published_at', 'yt_channel_videos', ['published_at'])

    # 2. yt_video_stats 테이블 생성
    op.create_table(
        'yt_video_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('yt_channel_videos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('view_count', sa.BigInteger(), nullable=True),
        sa.Column('like_count', sa.Integer(), nullable=True),
        sa.Column('comment_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # yt_video_stats 인덱스
    op.create_unique_constraint('uq_video_stats_date', 'yt_video_stats', ['video_id', 'date'])
    op.create_index('ix_video_stats_video_id', 'yt_video_stats', ['video_id'])
    op.create_index('ix_video_stats_date', 'yt_video_stats', ['date'])


def downgrade() -> None:
    # yt_video_stats 삭제
    op.drop_index('ix_video_stats_date', table_name='yt_video_stats')
    op.drop_index('ix_video_stats_video_id', table_name='yt_video_stats')
    op.drop_constraint('uq_video_stats_date', 'yt_video_stats', type_='unique')
    op.drop_table('yt_video_stats')

    # yt_channel_videos 삭제
    op.drop_index('ix_channel_videos_published_at', table_name='yt_channel_videos')
    op.drop_index('ix_channel_videos_channel_id', table_name='yt_channel_videos')
    op.drop_constraint('uq_channel_video', 'yt_channel_videos', type_='unique')
    op.drop_table('yt_channel_videos')
