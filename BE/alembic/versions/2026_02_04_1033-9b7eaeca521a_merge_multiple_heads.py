"""merge multiple heads

Revision ID: 9b7eaeca521a
Revises: d4e5f6a7b8c9, 5bfe83951480
Create Date: 2026-02-04 10:33:27.348888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b7eaeca521a'
down_revision: Union[str, None] = ('d4e5f6a7b8c9', '5bfe83951480')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
