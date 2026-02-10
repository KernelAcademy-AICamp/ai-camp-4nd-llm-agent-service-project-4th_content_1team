"""add video analysis tables and columns

페르소나 고도화를 위한 영상 분석 테이블 및 컬럼 추가.
- yt_my_video_analysis: 내 채널 영상별 자막 기반 분석 결과
- channel_personas: video_types, content_structures, tone_manner 컬럼 추가

Revision ID: f1a2b3c4d5e6
Revises: 9b7eaeca521a
Create Date: 2026-02-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = '9b7eaeca521a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. yt_my_video_analysis 테이블 생성
    op.create_table(
        'yt_my_video_analysis',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.String(), sa.ForeignKey('youtube_channels.channel_id', ondelete='CASCADE'), nullable=False),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('yt_channel_videos.id', ondelete='CASCADE'), nullable=False),

        # 분석 결과
        sa.Column('video_type', sa.String(), nullable=True),
        sa.Column('content_structure', sa.Text(), nullable=True),
        sa.Column('tone_manner', sa.Text(), nullable=True),
        sa.Column('key_topics', postgresql.JSONB(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('strengths', postgresql.JSONB(), nullable=True),
        sa.Column('weaknesses', postgresql.JSONB(), nullable=True),
        sa.Column('performance_insight', sa.Text(), nullable=True),

        # 자막 원본
        sa.Column('transcript_text', sa.Text(), nullable=True),

        # 메타
        sa.Column('selection_reason', sa.String(), nullable=False),
        sa.Column('analyzed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index('ix_yt_my_video_analysis_channel_id', 'yt_my_video_analysis', ['channel_id'])
    op.create_index('ix_yt_my_video_analysis_video_id', 'yt_my_video_analysis', ['video_id'])

    # 2. channel_personas 테이블에 컬럼 추가
    op.add_column('channel_personas', sa.Column('video_types', postgresql.JSONB(), nullable=True))
    op.add_column('channel_personas', sa.Column('content_structures', postgresql.JSONB(), nullable=True))
    op.add_column('channel_personas', sa.Column('tone_manner', sa.Text(), nullable=True))


def downgrade() -> None:
    # channel_personas 컬럼 제거
    op.drop_column('channel_personas', 'tone_manner')
    op.drop_column('channel_personas', 'content_structures')
    op.drop_column('channel_personas', 'video_types')

    # yt_my_video_analysis 테이블 제거
    op.drop_index('ix_yt_my_video_analysis_video_id', table_name='yt_my_video_analysis')
    op.drop_index('ix_yt_my_video_analysis_channel_id', table_name='yt_my_video_analysis')
    op.drop_table('yt_my_video_analysis')
