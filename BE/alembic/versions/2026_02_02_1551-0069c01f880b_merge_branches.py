"""merge branches

Revision ID: 0069c01f880b
Revises: c7d8e9f0a1b2, c3d4e5f6g7h9
Create Date: 2026-02-02 15:51:41.143751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0069c01f880b'
down_revision: Union[str, None] = ('c7d8e9f0a1b2', 'c3d4e5f6g7h9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
