"""
Topic Recommendation Engine - State Definition
LangGraph State for managing workflow data
"""

from typing import TypedDict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TrendItem:
    """수집된 트렌드 아이템"""
    source: str
    original_id: str
    title: str
    content: str
    link: str
    engagement: int
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 카테고리 정보
    preset_category: Optional[str] = None
    ai_category: Optional[str] = None
    ai_sub_category: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_tags: Optional[list[str]] = None
    ai_sentiment: Optional[str] = None

    # 점수
    trend_score: float = 0.0
    cluster_id: Optional[str] = None

    # 소스 레이어 (core / adjacent)
    source_layer: Optional[str] = None


@dataclass
class TrendTopic:
    """트렌드 토픽 (소분류) - 서브카테고리 내의 구체적인 트렌드 흐름"""
    topic_id: str
    name: str                       # "GPT-5 출시", "AI Agent 열풍" 등
    keywords: list[str]
    items: list[TrendItem]
    item_count: int = 0
    avg_score: float = 0.0
    trend_score: float = 0.0        # 이 토픽의 핫한 정도


@dataclass
class SubCategoryCluster:
    """서브카테고리 클러스터 (중분류) - Technology > AI, SW, Security 등"""
    sub_category: str               # "AI", "SW", "Security" 등
    keywords: list[str]
    items: list[TrendItem]
    topics: list[TrendTopic]        # 이 서브카테고리 내의 트렌드 토픽들

    item_count: int = 0
    avg_score: float = 0.0
    cluster_score: float = 0.0
    source_distribution: dict = field(default_factory=dict)


@dataclass
class CategoryCluster:
    """카테고리 클러스터 (대분류) - Technology, Economy 등"""
    category: str                   # "Technology", "Economy" 등
    sub_categories: list[SubCategoryCluster]

    item_count: int = 0
    avg_score: float = 0.0
    top_keywords: list[str] = field(default_factory=list)


@dataclass
class TopicCluster:
    """토픽 클러스터 (기존 호환용)"""
    cluster_id: str
    name: str
    keywords: list[str]
    items: list[TrendItem]

    item_count: int = 0
    total_engagement: int = 0
    avg_score: float = 0.0
    cluster_score: float = 0.0

    source_distribution: dict = field(default_factory=dict)
    trend_summary: str = ""
    rank: int = 0


@dataclass
class Recommendation:
    """최종 추천 결과"""
    title: str
    based_on_topic: str
    trend_basis: str
    recommendation_reason: str
    search_keywords: dict
    content_angles: list[str]
    thumbnail_idea: str
    urgency: str = "normal"


class TopicRecState(TypedDict, total=False):
    """
    LangGraph State for Topic Recommendation Engine

    각 노드는 이 State를 읽고 업데이트합니다.
    """
    # 입력
    persona: dict                           # 유저 페르소나

    # 소스 선택 단계 (Source Selector Agent 결과)
    source_config: dict                     # {"core": {...}, "adjacent": {...}}

    # 수집 단계
    trends: list[TrendItem]                 # 수집된 트렌드

    # 전처리 단계
    processed_trends: list[TrendItem]       # 전처리된 트렌드

    # 클러스터링 단계 (계층 구조)
    category_clusters: list[CategoryCluster]  # 카테고리별 계층 클러스터
    clusters: list[TopicCluster]              # 기존 호환용 클러스터

    # 분석 단계
    insights: dict                          # 트렌드 인사이트

    # 추천 단계
    recommendations: list[Recommendation]   # 최종 추천

    # 메타 정보
    retry_count: int                        # 재시도 횟수
    error: Optional[str]                    # 에러 메시지
    current_step: str                       # 현재 단계
