"""add competitor_channels table

Revision ID: a1b2c3d4e5f7
Revises: 9b7eaeca521a
Create Date: 2026-02-04 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f7'
down_revision = '9b7eaeca521a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'competitor_channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel_id', sa.String(), nullable=False),
        
        # YouTube 채널 정보
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('custom_url', sa.String(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        
        # 통계
        sa.Column('subscriber_count', sa.Integer(), default=0),
        sa.Column('view_count', sa.BigInteger(), default=0),
        sa.Column('video_count', sa.Integer(), default=0),
        
        # 추가 메타데이터
        sa.Column('topic_categories', postgresql.JSONB(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        
        # AI 분석 결과
        sa.Column('strengths', postgresql.JSONB(), nullable=True),
        sa.Column('channel_personality', sa.Text(), nullable=True),
        sa.Column('target_audience', sa.Text(), nullable=True),
        sa.Column('content_style', sa.Text(), nullable=True),
        sa.Column('analysis_json', postgresql.JSONB(), nullable=True),
        
        # 추가 정보
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        
        # 메타
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reference_channel_id', sa.String(), sa.ForeignKey('youtube_channels.channel_id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # 인덱스
    op.create_index('ix_competitor_channels_user_id', 'competitor_channels', ['user_id'])
    op.create_index('ix_competitor_channels_channel_id', 'competitor_channels', ['channel_id'])
    op.create_index('ix_competitor_channels_reference_channel_id', 'competitor_channels', ['reference_channel_id'])
    
    # user_id + channel_id 복합 unique 제약
    op.create_unique_constraint(
        'uq_competitor_channels_user_channel',
        'competitor_channels',
        ['user_id', 'channel_id']
    )
    
    # competitor_channel_videos 테이블 생성
    op.create_table(
        'competitor_channel_videos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('competitor_channel_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('competitor_channels.id', ondelete='CASCADE'), nullable=False),
        
        # YouTube 영상 정보
        sa.Column('video_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration', sa.String(), nullable=True),
        
        # 통계
        sa.Column('view_count', sa.Integer(), default=0),
        sa.Column('like_count', sa.Integer(), default=0),
        sa.Column('comment_count', sa.Integer(), default=0),
        
        # AI 분석 결과
        sa.Column('analysis_summary', sa.Text(), nullable=True),  # 핵심 내용
        sa.Column('analysis_strengths', postgresql.JSONB(), nullable=True),  # 영상 장점
        sa.Column('analysis_weaknesses', postgresql.JSONB(), nullable=True),  # 부족한 점
        sa.Column('audience_reaction', sa.Text(), nullable=True),  # 시청자 반응
        
        # 메타
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # 인덱스
    op.create_index('ix_competitor_channel_videos_competitor_channel_id', 
                    'competitor_channel_videos', ['competitor_channel_id'])
    op.create_index('ix_competitor_channel_videos_video_id', 
                    'competitor_channel_videos', ['video_id'])


def downgrade() -> None:
    # competitor_channel_videos 삭제
    op.drop_index('ix_competitor_channel_videos_video_id', 'competitor_channel_videos')
    op.drop_index('ix_competitor_channel_videos_competitor_channel_id', 'competitor_channel_videos')
    op.drop_table('competitor_channel_videos')
    
    # competitor_channels 삭제
    op.drop_constraint('uq_competitor_channels_user_channel', 'competitor_channels')
    op.drop_index('ix_competitor_channels_reference_channel_id', 'competitor_channels')
    op.drop_index('ix_competitor_channels_channel_id', 'competitor_channels')
    op.drop_index('ix_competitor_channels_user_id', 'competitor_channels')
    op.drop_table('competitor_channels')
