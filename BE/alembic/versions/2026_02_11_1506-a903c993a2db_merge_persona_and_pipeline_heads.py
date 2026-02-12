"""merge_persona_and_pipeline_heads

Revision ID: a903c993a2db
Revises: h2i3j4k5l6m7, i9j0k1l2m3n4
Create Date: 2026-02-11 15:06:30.554286

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a903c993a2db'
down_revision: Union[str, None] = ('h2i3j4k5l6m7', 'i9j0k1l2m3n4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
