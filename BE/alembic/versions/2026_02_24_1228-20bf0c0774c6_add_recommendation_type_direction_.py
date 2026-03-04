"""add recommendation_type, direction, source_layer to trend_topics

Revision ID: 20bf0c0774c6
Revises: 9dd1286e783e
Create Date: 2026-02-24 12:28:31.764065

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20bf0c0774c6'
down_revision: Union[str, None] = '9dd1286e783e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('trend_topics', sa.Column('recommendation_type', sa.String(length=20), nullable=True, comment='viewer_needs | hit_pattern | channel_expansion'))
    op.add_column('trend_topics', sa.Column('recommendation_direction', sa.Text(), nullable=True, comment='영상 방향성 제안 멘트'))
    op.add_column('trend_topics', sa.Column('source_layer', sa.String(length=10), nullable=True, comment='core | adjacent'))


def downgrade() -> None:
    op.drop_column('trend_topics', 'source_layer')
    op.drop_column('trend_topics', 'recommendation_direction')
    op.drop_column('trend_topics', 'recommendation_type')
