"""empty message

Revision ID: 5bfe83951480
Revises: d1e2f3a4b5c6, 0069c01f880b
Create Date: 2026-02-03 16:59:04.664637

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bfe83951480'
down_revision: Union[str, None] = ('d1e2f3a4b5c6', '0069c01f880b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
