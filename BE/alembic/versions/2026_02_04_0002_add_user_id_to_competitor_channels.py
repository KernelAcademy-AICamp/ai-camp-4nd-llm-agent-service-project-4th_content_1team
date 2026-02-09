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
    # competitor_channels 테이블에 user_id 컬럼 추가
    op.add_column(
        'competitor_channels',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # FK 제약 추가
    op.create_foreign_key(
        'fk_competitor_channels_user_id',
        'competitor_channels',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # 인덱스 추가
    op.create_index(
        'ix_competitor_channels_user_id',
        'competitor_channels',
        ['user_id']
    )
    
    # unique 제약 추가 (user_id + channel_id)
    op.create_unique_constraint(
        'uq_competitor_channels_user_channel',
        'competitor_channels',
        ['user_id', 'channel_id']
    )
    
    # 기존 channel_id unique 제약 제거 (user별로 같은 channel 추가 가능하도록)
    op.drop_index('ix_competitor_channels_channel_id', 'competitor_channels')
    op.create_index(
        'ix_competitor_channels_channel_id',
        'competitor_channels',
        ['channel_id'],
        unique=False
    )


def downgrade() -> None:
    # 원복
    op.drop_constraint('uq_competitor_channels_user_channel', 'competitor_channels')
    op.drop_index('ix_competitor_channels_user_id', 'competitor_channels')
    op.drop_constraint('fk_competitor_channels_user_id', 'competitor_channels')
    op.drop_column('competitor_channels', 'user_id')
    
    # channel_id unique 복원
    op.drop_index('ix_competitor_channels_channel_id', 'competitor_channels')
    op.create_index(
        'ix_competitor_channels_channel_id',
        'competitor_channels',
        ['channel_id'],
        unique=True
    )
