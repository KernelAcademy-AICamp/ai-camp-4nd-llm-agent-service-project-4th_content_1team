"""add channel_personas table

채널 페르소나 테이블 추가.
규칙 기반 + LLM 해석 결과를 저장합니다.

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-01 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'channel_personas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.String(), sa.ForeignKey('youtube_channels.channel_id', ondelete='CASCADE'), unique=True, nullable=False),

        # 종합 서술
        sa.Column('persona_summary', sa.Text(), nullable=True),

        # 정체성
        sa.Column('one_liner', sa.String(), nullable=True),
        sa.Column('main_topics', postgresql.JSONB(), nullable=True),
        sa.Column('content_style', sa.String(), nullable=True),
        sa.Column('differentiator', sa.String(), nullable=True),

        # 타겟 시청자
        sa.Column('target_audience', sa.String(), nullable=True),
        sa.Column('audience_needs', sa.String(), nullable=True),

        # 성공 공식
        sa.Column('hit_topics', postgresql.JSONB(), nullable=True),
        sa.Column('title_patterns', postgresql.JSONB(), nullable=True),
        sa.Column('optimal_duration', sa.String(), nullable=True),

        # 성장 기회
        sa.Column('growth_opportunities', postgresql.JSONB(), nullable=True),

        # 근거
        sa.Column('evidence', postgresql.JSONB(), nullable=True),

        # 매칭용 키워드
        sa.Column('topic_keywords', postgresql.JSONB(), nullable=True),
        sa.Column('style_keywords', postgresql.JSONB(), nullable=True),

        # 메타
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index('ix_channel_personas_channel_id', 'channel_personas', ['channel_id'])


def downgrade() -> None:
    op.drop_index('ix_channel_personas_channel_id', table_name='channel_personas')
    op.drop_table('channel_personas')
