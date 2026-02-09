"""add hit/low patterns columns

히트/저조 비교 분석 결과 컬럼 추가.
- hit_patterns: 히트 영상 공통 패턴
- low_patterns: 저조 영상 공통 패턴
- success_formula: 성공 공식

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-02-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # channel_personas 테이블에 히트/저조 비교 분석 컬럼 추가
    op.add_column('channel_personas', sa.Column('hit_patterns', JSONB, nullable=True))
    op.add_column('channel_personas', sa.Column('low_patterns', JSONB, nullable=True))
    op.add_column('channel_personas', sa.Column('success_formula', sa.Text(), nullable=True))


def downgrade() -> None:
    # 컬럼 제거
    op.drop_column('channel_personas', 'success_formula')
    op.drop_column('channel_personas', 'low_patterns')
    op.drop_column('channel_personas', 'hit_patterns')
