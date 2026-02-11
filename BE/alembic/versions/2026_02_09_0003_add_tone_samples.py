"""add tone_samples column

말투 샘플 문장 컬럼 추가.
스크립트 생성 시 few-shot 예시로 활용.

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-02-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'h2i3j4k5l6m7'
down_revision: Union[str, None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # channel_personas 테이블에 tone_samples 컬럼 추가
    op.add_column('channel_personas', sa.Column('tone_samples', JSONB, nullable=True))


def downgrade() -> None:
    # 컬럼 제거
    op.drop_column('channel_personas', 'tone_samples')
