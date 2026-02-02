"""add topic_recommendations table

트렌드 기반 주제 추천 결과를 저장하는 테이블.
채널당 1개, 24시간 단위로 갱신됩니다.

Revision ID: c3d4e5f6g7h8
Revises: c3d4e5f6g7h7
Create Date: 2026-02-02 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'topic_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.String(), sa.ForeignKey('youtube_channels.channel_id', ondelete='CASCADE'), unique=True, nullable=False),

        # 추천 결과
        sa.Column('recommendations', postgresql.JSONB(), nullable=False, server_default='[]'),

        # 메타데이터
        sa.Column('generated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('persona_snapshot', postgresql.JSONB(), nullable=True),
    )

    op.create_index('ix_topic_recommendations_channel_id', 'topic_recommendations', ['channel_id'])
    op.create_index('ix_topic_recommendations_expires_at', 'topic_recommendations', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_topic_recommendations_expires_at', table_name='topic_recommendations')
    op.drop_index('ix_topic_recommendations_channel_id', table_name='topic_recommendations')
    op.drop_table('topic_recommendations')
