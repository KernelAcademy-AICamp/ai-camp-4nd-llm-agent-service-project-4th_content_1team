"""
스크립트 생성 파이프라인 - 중간 결과물 모델

CONTENT_BRIEFS: Planner 결과
ARTICLE_SETS / ARTICLES / ARTICLE_ASSETS: 뉴스 수집 결과
FACT_SETS / FACTS / FACT_EVIDENCES / FACT_DEDUPE_CLUSTERS: 팩트 추출 결과
VISUAL_PLANS: 시각자료 제안
INSIGHT_SENTENCES: 핵심 인사이트 문장
INSIGHT_PACKS: Insight Builder 결과
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, Float, Boolean, ForeignKey,
    UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.db import Base


# =============================================================================
# Planner
# =============================================================================

class ContentBrief(Base):
    """
    Planner가 생성한 콘텐츠 기획안
    
    brief_json 안에 챕터 구성, 뉴스 쿼리, 앵글 등이 들어있음.
    """
    __tablename__ = "content_briefs"

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

    selected_angle = Column(String(500), nullable=True)
    brief_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_content_briefs_topic_request_id", "topic_request_id"),
    )


# =============================================================================
# News Research
# =============================================================================

class ArticleSet(Base):
    """
    뉴스 수집 세트
    
    한 번의 News Research 실행으로 수집된 기사 묶음.
    query_json에 어떤 검색어로 수집했는지 기록.
    """
    __tablename__ = "article_sets"

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

    query_json = Column(JSONB, nullable=True)  # 검색어 목록
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_article_sets_topic_request_id", "topic_request_id"),
    )


class Article(Base):
    """
    개별 뉴스 기사
    
    크롤링으로 수집된 기사 한 건.
    url은 같은 세트 안에서만 유니크 (다른 토픽에서는 같은 기사 수집 가능).
    """
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_set_id = Column(
        UUID(as_uuid=True),
        ForeignKey("article_sets.id", ondelete="CASCADE"),
        nullable=False,
    )

    url = Column(Text, nullable=False)
    publisher = Column(String(200), nullable=True)
    title = Column(String(500), nullable=False)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    content_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    top_quotes = Column(JSONB, nullable=True)
    raw_extraction_json = Column(JSONB, nullable=True)
    paywalled = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("article_set_id", "url", name="uq_articles_set_url"),
        Index("ix_articles_article_set_id", "article_set_id"),
    )


class ArticleAsset(Base):
    """
    기사에 포함된 이미지/차트/표
    
    url에는 로컬 경로 저장 (/images/news/abc.png).
    meta_json에 원본 URL, 크기 등 부가 정보.
    """
    __tablename__ = "article_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )

    kind = Column(String(30), nullable=False)  # og_image | image | table_html
    url = Column(Text, nullable=True)  # 로컬 경로
    table_html = Column(Text, nullable=True)
    meta_json = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_article_assets_article_id", "article_id"),
    )


# =============================================================================
# Fact Extraction
# =============================================================================

class FactSet(Base):
    """팩트 추출 세트 — 한 번의 Fact Extractor 실행 결과 묶음."""
    __tablename__ = "fact_sets"

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
    warnings_json = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_fact_sets_topic_request_id", "topic_request_id"),
    )


class Fact(Base):
    """
    개별 팩트
    
    type: stat(통계), event(사건), definition(정의), trend(트렌드), quote(인용)
    hash: 중복 검출용 해시
    """
    __tablename__ = "facts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fact_set_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fact_sets.id", ondelete="CASCADE"),
        nullable=False,
    )

    type = Column(String(30), nullable=False)  # stat | event | definition | trend | quote
    claim = Column(Text, nullable=False)
    entities = Column(JSONB, nullable=True)
    numbers = Column(JSONB, nullable=True)
    time_json = Column(JSONB, nullable=True)
    confidence = Column(Float, nullable=True)
    tags = Column(JSONB, nullable=True)
    hash = Column(String(64), nullable=True, index=True)

    __table_args__ = (
        Index("ix_facts_fact_set_id", "fact_set_id"),
    )


class FactEvidence(Base):
    """팩트의 근거 — 어떤 기사의 어떤 문장에서 추출됐는지."""
    __tablename__ = "fact_evidences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facts.id", ondelete="CASCADE"),
        nullable=False,
    )
    article_id = Column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )

    snippet = Column(Text, nullable=False)
    locator_json = Column(JSONB, nullable=True)
    asset_refs = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_fact_evidences_fact_id", "fact_id"),
        Index("ix_fact_evidences_article_id", "article_id"),
    )


class FactDedupeCluster(Base):
    """중복 팩트 클러스터 — 같은 내용의 팩트들을 하나로 묶음."""
    __tablename__ = "fact_dedupe_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fact_set_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fact_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    canonical_fact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("facts.id", ondelete="CASCADE"),
        nullable=False,
    )

    merged_fact_ids = Column(JSONB, nullable=False)
    reason = Column(Text, nullable=True)


class VisualPlan(Base):
    """시각 자료 제안 — 표, 차트, 타임라인 등."""
    __tablename__ = "visual_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fact_set_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fact_sets.id", ondelete="CASCADE"),
        nullable=False,
    )

    type = Column(String(30), nullable=False)  # table | chart | timeline | comparison_table
    purpose = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)
    fact_ids = Column(JSONB, nullable=True)
    data_spec = Column(JSONB, nullable=True)
    source_refs = Column(JSONB, nullable=True)


class InsightSentence(Base):
    """핵심 인사이트 문장 — 통념 깨기, 논란, 기회 등."""
    __tablename__ = "insight_sentences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fact_set_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fact_sets.id", ondelete="CASCADE"),
        nullable=False,
    )

    sentence = Column(Text, nullable=False)
    label = Column(String(30), nullable=False)
    # myth_busting | controversy | risk | opportunity | cause_effect | turning_point
    why_it_matters = Column(Text, nullable=True)
    evidence_json = Column(JSONB, nullable=True)


# =============================================================================
# Insight Builder
# =============================================================================

class InsightPack(Base):
    """
    Insight Builder 결과
    
    draft_json: Pass 1 초안 (디버깅용)
    insight_json: Pass 2 최종 전략
    """
    __tablename__ = "insight_packs"

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
    draft_json = Column(JSONB, nullable=True)    # Pass 1 초안 (디버깅용)
    insight_json = Column(JSONB, nullable=False)  # Pass 2 최종 결과

    __table_args__ = (
        Index("ix_insight_packs_topic_request_id", "topic_request_id"),
    )
