"""add viewer analysis columns

댓글 기반 시청자 분석 컬럼 추가.

channel_personas:
- viewer_likes: 히트 영상에서 시청자가 좋아하는 것
- viewer_dislikes: 저조 영상에서 시청자가 싫어하는 것
- current_viewer_needs: 최신 시청자 니즈 (최근 영상 가중)

yt_my_video_analysis:
- viewer_reactions: 시청자 반응 (댓글 기반)
- viewer_needs: 시청자 니즈/요청사항
- performance_reason: 이 영상이 hit/low인 이유

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-02-11 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'k2l3m4n5o6p7'
down_revision: Union[str, None] = 'j1k2l3m4n5o6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_yt_my_video_analysis_exists() -> None:
    """yt_my_video_analysis 테이블이 없으면 생성 (병합 경로에서 f1a2b3c4d5e6가 스킵된 경우 대비)."""
    conn = op.get_bind()
    if "yt_my_video_analysis" in inspect(conn).get_table_names():
        return
    op.create_table(
        'yt_my_video_analysis',
        sa.Column('id', PG_UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.String(), sa.ForeignKey('youtube_channels.channel_id', ondelete='CASCADE'), nullable=False),
        sa.Column('video_id', PG_UUID(as_uuid=True), sa.ForeignKey('yt_channel_videos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('video_type', sa.String(), nullable=True),
        sa.Column('content_structure', sa.Text(), nullable=True),
        sa.Column('tone_manner', sa.Text(), nullable=True),
        sa.Column('key_topics', JSONB, nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('strengths', JSONB, nullable=True),
        sa.Column('weaknesses', JSONB, nullable=True),
        sa.Column('performance_insight', sa.Text(), nullable=True),
        sa.Column('transcript_text', sa.Text(), nullable=True),
        sa.Column('selection_reason', sa.String(), nullable=False),
        sa.Column('analyzed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_yt_my_video_analysis_channel_id', 'yt_my_video_analysis', ['channel_id'])
    op.create_index('ix_yt_my_video_analysis_video_id', 'yt_my_video_analysis', ['video_id'])


def upgrade() -> None:
    # channel_personas 테이블에 시청자 분석 컬럼 추가
    op.add_column('channel_personas', sa.Column('viewer_likes', JSONB, nullable=True))
    op.add_column('channel_personas', sa.Column('viewer_dislikes', JSONB, nullable=True))
    op.add_column('channel_personas', sa.Column('current_viewer_needs', JSONB, nullable=True))

    # yt_my_video_analysis 없으면 먼저 생성 후 컬럼 추가
    _ensure_yt_my_video_analysis_exists()
    op.add_column('yt_my_video_analysis', sa.Column('viewer_reactions', JSONB, nullable=True))
    op.add_column('yt_my_video_analysis', sa.Column('viewer_needs', JSONB, nullable=True))
    op.add_column('yt_my_video_analysis', sa.Column('performance_reason', sa.Text, nullable=True))


def downgrade() -> None:
    # yt_my_video_analysis 컬럼 제거
    op.drop_column('yt_my_video_analysis', 'performance_reason')
    op.drop_column('yt_my_video_analysis', 'viewer_needs')
    op.drop_column('yt_my_video_analysis', 'viewer_reactions')

    # channel_personas 컬럼 제거
    op.drop_column('channel_personas', 'current_viewer_needs')
    op.drop_column('channel_personas', 'viewer_dislikes')
    op.drop_column('channel_personas', 'viewer_likes')
