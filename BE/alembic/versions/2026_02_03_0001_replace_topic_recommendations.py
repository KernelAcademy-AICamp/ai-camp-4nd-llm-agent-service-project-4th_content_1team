"""Replace topic_recommendations with channel_topics and trend_topics

Revision ID: a1b2c3d4e5f6
Revises: 0069c01f880b
Create Date: 2026-02-03

기존 topic_recommendations (JSON 덩어리) 삭제하고
channel_topics, trend_topics (개별 Row) 테이블 생성
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = '0069c01f880b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 기존 topic_recommendations 테이블 삭제
    op.drop_table('topic_recommendations')

    # 2. channel_topics 테이블 생성 (채널 맞춤 추천 - 주간)
    op.create_table(
        'channel_topics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.String(), sa.ForeignKey('youtube_channels.channel_id', ondelete='CASCADE'), nullable=False),

        # 순위 및 표시 상태
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('display_status', sa.String(20), nullable=False, default='queued'),

        # 콘텐츠 정보
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('based_on_topic', sa.String(100), nullable=True),
        sa.Column('trend_basis', sa.Text(), nullable=True),
        sa.Column('recommendation_reason', sa.Text(), nullable=True),
        sa.Column('urgency', sa.String(20), default='normal'),
        sa.Column('search_keywords', postgresql.JSONB(), default=list),
        sa.Column('content_angles', postgresql.JSONB(), default=list),
        sa.Column('thumbnail_idea', sa.Text(), nullable=True),

        # 상태 관리
        sa.Column('status', sa.String(20), nullable=False, default='recommended'),
        sa.Column('scheduled_date', sa.Date(), nullable=True),

        # 연결
        sa.Column('script_id', postgresql.UUID(as_uuid=True), nullable=True),

        # 시간 정보
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 인덱스 생성
    op.create_index('ix_channel_topics_channel_id', 'channel_topics', ['channel_id'])
    op.create_index('ix_channel_topics_display_status', 'channel_topics', ['display_status'])
    op.create_index('ix_channel_topics_status', 'channel_topics', ['status'])

    # 3. trend_topics 테이블 생성 (트렌드 기반 추천 - 일간)
    op.create_table(
        'trend_topics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.String(), sa.ForeignKey('youtube_channels.channel_id', ondelete='CASCADE'), nullable=False),

        # 순위 및 표시 상태
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('display_status', sa.String(20), nullable=False, default='queued'),

        # 콘텐츠 정보
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('based_on_topic', sa.String(100), nullable=True),
        sa.Column('trend_basis', sa.Text(), nullable=True),
        sa.Column('recommendation_reason', sa.Text(), nullable=True),
        sa.Column('urgency', sa.String(20), default='urgent'),
        sa.Column('search_keywords', postgresql.JSONB(), default=list),
        sa.Column('content_angles', postgresql.JSONB(), default=list),
        sa.Column('thumbnail_idea', sa.Text(), nullable=True),

        # 상태 관리
        sa.Column('status', sa.String(20), nullable=False, default='recommended'),
        sa.Column('scheduled_date', sa.Date(), nullable=True),

        # 연결
        sa.Column('script_id', postgresql.UUID(as_uuid=True), nullable=True),

        # 시간 정보
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 인덱스 생성
    op.create_index('ix_trend_topics_channel_id', 'trend_topics', ['channel_id'])
    op.create_index('ix_trend_topics_display_status', 'trend_topics', ['display_status'])
    op.create_index('ix_trend_topics_status', 'trend_topics', ['status'])


def downgrade() -> None:
    # trend_topics 삭제
    op.drop_index('ix_trend_topics_status', 'trend_topics')
    op.drop_index('ix_trend_topics_display_status', 'trend_topics')
    op.drop_index('ix_trend_topics_channel_id', 'trend_topics')
    op.drop_table('trend_topics')

    # channel_topics 삭제
    op.drop_index('ix_channel_topics_status', 'channel_topics')
    op.drop_index('ix_channel_topics_display_status', 'channel_topics')
    op.drop_index('ix_channel_topics_channel_id', 'channel_topics')
    op.drop_table('channel_topics')

    # topic_recommendations 복원
    op.create_table(
        'topic_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.String(), sa.ForeignKey('youtube_channels.channel_id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('recommendations', postgresql.JSONB(), nullable=False, default=list),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('persona_snapshot', postgresql.JSONB(), nullable=True),
    )
