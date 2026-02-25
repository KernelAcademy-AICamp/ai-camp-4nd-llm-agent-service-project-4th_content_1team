"""merge_multiple_heads_feb25

Revision ID: 0a1cfcc735f5
Revises: k2l3m4n5o6p7, a903c993a2db
Create Date: 2026-02-25 10:45:13.585341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a1cfcc735f5'
down_revision: Union[str, None] = ('k2l3m4n5o6p7', 'a903c993a2db')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
