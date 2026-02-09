"""add applicable_points column and recent_video_captions table

Revision ID: a1b2c3d4e5f6
Revises: f6g7h8i9j0k1
Create Date: 2026-02-09 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'g7h8i9j0k1l2'
down_revision = 'f6g7h8i9j0k1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. applicable_points 컬럼 추가
    op.add_column(
        'competitor_recent_videos',
        sa.Column('applicable_points', postgresql.JSONB(), nullable=True)
    )

    # 2. recent_video_captions 테이블 생성 (이미 존재하면 skip)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'recent_video_captions' not in inspector.get_table_names():
        op.create_table(
            'recent_video_captions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('recent_video_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('competitor_recent_videos.id', ondelete='CASCADE'),
                      nullable=False, unique=True),
            sa.Column('segments_json', postgresql.JSONB(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text('now()')),
        )
        op.create_index('ix_recent_video_captions_recent_video_id',
                        'recent_video_captions', ['recent_video_id'])


def downgrade() -> None:
    op.drop_column('competitor_recent_videos', 'applicable_points')
    # captions 테이블은 다른 migration에서 관리할 수 있으므로 여기서는 삭제하지 않음
