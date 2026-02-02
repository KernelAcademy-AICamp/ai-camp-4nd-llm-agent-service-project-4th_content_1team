"""add category fields to channel_personas

페르소나에 카테고리 필드 추가:
- analyzed_categories/subcategories: 채널 분석에서 자동 추출
- preferred_categories/subcategories: 사용자 선택

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-01 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 채널 분석에서 자동 추출
    op.add_column('channel_personas', sa.Column('analyzed_categories', postgresql.JSONB(), nullable=True))
    op.add_column('channel_personas', sa.Column('analyzed_subcategories', postgresql.JSONB(), nullable=True))

    # 사용자가 온보딩에서 선택
    op.add_column('channel_personas', sa.Column('preferred_categories', postgresql.JSONB(), nullable=True))
    op.add_column('channel_personas', sa.Column('preferred_subcategories', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('channel_personas', 'preferred_subcategories')
    op.drop_column('channel_personas', 'preferred_categories')
    op.drop_column('channel_personas', 'analyzed_subcategories')
    op.drop_column('channel_personas', 'analyzed_categories')
