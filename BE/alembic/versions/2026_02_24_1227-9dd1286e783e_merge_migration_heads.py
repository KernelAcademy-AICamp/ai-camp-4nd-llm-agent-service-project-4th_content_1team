"""merge migration heads

Revision ID: 9dd1286e783e
Revises: k2l3m4n5o6p7, a903c993a2db
Create Date: 2026-02-24 12:27:29.870887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9dd1286e783e'
down_revision: Union[str, None] = ('k2l3m4n5o6p7', 'a903c993a2db')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
