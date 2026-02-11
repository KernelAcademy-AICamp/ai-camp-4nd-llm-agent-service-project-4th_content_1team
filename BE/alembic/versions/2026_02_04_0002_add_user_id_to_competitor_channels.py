"""add user_id to competitor_channels

Revision ID: b2c3d4e5f6g8
Revises: a1b2c3d4e5f7
Create Date: 2026-02-04 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g8'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 이미 add_competitor_channels_table.py에서 모두 생성됨 (중복 방지)
    pass


def downgrade() -> None:
    # 이미 add_competitor_channels_table.py에서 처리됨
    pass
