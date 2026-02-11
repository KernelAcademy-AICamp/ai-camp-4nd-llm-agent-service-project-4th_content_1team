"""merge all heads: h2i3j4k5l6m7 + i9j0k1l2m3n4

두 브랜치 통합:
- Branch 1: 페르소나 영상 분석 (tone_samples)
- Branch 2: 경쟁자 채널 분석 (comment_insights)

Revision ID: j1k2l3m4n5o6
Revises: h2i3j4k5l6m7, i9j0k1l2m3n4
Create Date: 2026-02-11 10:00:00.000000

"""
from typing import Union

revision: str = 'j1k2l3m4n5o6'
down_revision: Union[str, None] = ('h2i3j4k5l6m7', 'i9j0k1l2m3n4')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
