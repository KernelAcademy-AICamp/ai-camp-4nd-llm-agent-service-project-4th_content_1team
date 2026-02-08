"""
파이프라인 요청 및 에이전트 실행 이력

TOPIC_REQUESTS: 스크립트 생성 요청의 중심 허브
AGENT_RUNS: 각 에이전트(Planner, News Research 등) 실행 이력
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.db import Base


class TopicRequest(Base):
    """
    스크립트 생성 요청 (파이프라인 중심 허브)
    
    사용자가 "이 주제로 스크립트 만들어줘" 하면 여기에 한 줄 생김.
    이후 모든 에이전트 결과가 이 테이블의 id로 연결됨.
    """
    __tablename__ = "topic_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id = Column(
        String,
        ForeignKey("youtube_channels.channel_id", ondelete="SET NULL"),
        nullable=True,  # 초보모드: 채널 없이도 가능
    )
    
    topic_title = Column(String(300), nullable=False)
    topic_keywords = Column(JSONB, nullable=True)  # 사용자 직접 입력 키워드
    language = Column(String(10), nullable=False, default="ko")
    region = Column(String(10), nullable=False, default="KR")
    
    status = Column(
        String(20),
        nullable=False,
        default="created",
    )  # created | planned | researched | writing | verified | failed

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_topic_requests_user_id", "user_id"),
        Index("ix_topic_requests_status", "status"),
    )


class AgentRun(Base):
    """
    에이전트 실행 이력
    
    Planner, News Research 등 각 에이전트가 실행될 때마다 한 줄 생김.
    시작/종료 시간, 성공/실패, 에러 메시지 등을 기록.
    """
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("topic_requests.id", ondelete="CASCADE"),
        nullable=False,
    )

    agent_name = Column(String(50), nullable=False)  # planner, news_research, ...
    status = Column(
        String(20),
        nullable=False,
        default="queued",
    )  # queued | running | succeeded | failed

    input_json = Column(JSONB, nullable=True)
    output_ref = Column(JSONB, nullable=True)  # 결과 참조 (어떤 테이블에 저장됐는지)
    
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    metrics_json = Column(JSONB, nullable=True)  # 실행 시간, 토큰 수 등

    __table_args__ = (
        Index("ix_agent_runs_topic_request_id", "topic_request_id"),
        Index("ix_agent_runs_agent_name", "agent_name"),
    )
