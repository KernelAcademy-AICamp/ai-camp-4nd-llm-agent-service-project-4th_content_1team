"""
스크립트 생성 파이프라인 - 최종 결과물 모델

SCRIPT_DRAFTS: Writer가 생성한 스크립트 초안
SCRIPT_CLAIMS: 스크립트 내 주장 (팩트체크 대상)
SCRIPT_SOURCE_MAPS: 주장 ↔ 팩트/기사 매핑
VERIFIED_SCRIPTS: Verifier가 검증 완료한 최종 스크립트
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.db import Base


# =============================================================================
# Writer
# =============================================================================

class ScriptDraft(Base):
    """
    Writer가 생성한 스크립트 초안
    
    script_json: Hook + Chapters + Closing 전체 대본
    metadata_json: 제목, 예상 길이, 훅 타입 등
    """
    __tablename__ = "script_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("topic_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSONB, nullable=True)
    script_json = Column(JSONB, nullable=False)

    __table_args__ = (
        Index("ix_script_drafts_topic_request_id", "topic_request_id"),
    )


class ScriptClaim(Base):
    """
    스크립트 내 주장 (팩트체크 대상)
    
    Writer가 작성한 대본에서 검증이 필요한 주장들.
    Verifier가 이걸 보고 팩트체크함.
    """
    __tablename__ = "script_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    script_draft_id = Column(
        UUID(as_uuid=True),
        ForeignKey("script_drafts.id", ondelete="CASCADE"),
        nullable=False,
    )

    claim_text = Column(Text, nullable=False)
    type = Column(String(30), nullable=False)
    # stat | event | definition | trend | quote | opinion
    linked_fact_ids = Column(JSONB, nullable=True)
    risk_flags = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_script_claims_script_draft_id", "script_draft_id"),
    )


class ScriptSourceMap(Base):
    """
    주장 ↔ 팩트/기사 매핑
    
    "이 주장은 이 팩트에서 나왔고, 원본 기사는 여기야" 라는 연결고리.
    """
    __tablename__ = "script_source_maps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    script_draft_id = Column(
        UUID(as_uuid=True),
        ForeignKey("script_drafts.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("script_claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    fact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facts.id", ondelete="SET NULL"),
        nullable=True,
    )
    article_id = Column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
    )

    evidence_json = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_script_source_maps_script_draft_id", "script_draft_id"),
        Index("ix_script_source_maps_claim_id", "claim_id"),
    )


# =============================================================================
# Verifier
# =============================================================================

class VerifiedScript(Base):
    """
    Verifier가 검증 완료한 최종 스크립트
    
    verification_report_json: 검증 리포트 (통과/불통과 비트 수, 이슈 목록)
    changes_json: 수정 사항 (향후 자동 수정 기능용)
    """
    __tablename__ = "verified_scripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("topic_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    verified_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    final_script_json = Column(JSONB, nullable=True)
    final_text = Column(Text, nullable=True)
    source_map_json = Column(JSONB, nullable=True)
    changes_json = Column(JSONB, nullable=True)
    verification_report_json = Column(JSONB, nullable=True)  # 검증 리포트

    __table_args__ = (
        Index("ix_verified_scripts_topic_request_id", "topic_request_id"),
    )
