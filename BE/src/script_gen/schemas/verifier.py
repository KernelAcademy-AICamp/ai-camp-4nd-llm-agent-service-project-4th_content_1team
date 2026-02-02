"""
Verifier Schema - 팩트 체크 & 출처 정리
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ClaimType(str, Enum):
    """주장의 유형"""
    STATISTIC = "statistic"      # "40% 성장" - 반드시 검증
    EVENT = "event"              # "X사가 발표" - 검증 필요
    QUOTE = "quote"              # "CEO는 말했다" - 출처 필요
    TREND = "trend"              # "AI가 부상하고 있다" - 선택적 검증
    OPINION = "opinion"          # "AI는 중요하다" - 검증 불필요
    GENERAL = "general"          # "기술은 발전한다" - 검증 불필요


class VerificationAction(str, Enum):
    """검증 후 취할 행동"""
    KEEP = "keep"                # 그대로 유지
    DELETE = "delete"            # 삭제
    SOFTEN = "soften"            # 완화 ("40% 성장" → "크게 성장")
    ADD_SOURCE = "add_source"    # 출처 추가


class FactReference(BaseModel):
    """Fact 참조 정보"""
    fact_id: str
    fact_content: str = Field(description="Fact 원문 (처음 100자)")
    category: str = Field(description="Statistic, Event, Quote 등")
    confidence: float = Field(ge=0.0, le=1.0, description="매칭 신뢰도")


class SourceInfo(BaseModel):
    """출처 정보"""
    fact_id: str
    article_id: Optional[str] = None
    publisher: str
    published_date: Optional[str] = None
    url: Optional[str] = None
    snippet: str = Field(description="관련 문장 발췌")


class VerificationIssue(BaseModel):
    """검증 중 발견된 문제"""
    beat_id: str
    issue_type: Literal["missing_fact", "invalid_fact_id", "suspicious_claim", "no_source"]
    description: str
    severity: Literal["critical", "warning", "info"]
    suggested_action: VerificationAction


class BeatVerification(BaseModel):
    """Beat 단위 검증 결과"""
    beat_id: str
    beat_text: str
    fact_references: List[FactReference] = Field(default=[])
    issues: List[VerificationIssue] = Field(default=[])
    verified: bool = Field(description="이 Beat가 검증을 통과했는지")


class SourceMapEntry(BaseModel):
    """출처 맵 항목"""
    beat_id: str
    sentence: str = Field(description="출처가 필요한 문장")
    sources: List[SourceInfo]


class VerificationReport(BaseModel):
    """검증 리포트"""
    total_beats: int
    verified_beats: int
    total_fact_references: int
    valid_fact_references: int
    issues: List[VerificationIssue]
    suspicious_beats: List[str] = Field(default=[], description="Deep 검증이 필요한 Beat ID 리스트")


class VerifierOutput(BaseModel):
    """Verifier 최종 출력"""
    verified: bool = Field(description="전체 스크립트가 검증을 통과했는지")
    source_map: List[SourceMapEntry]
    verification_report: VerificationReport
    beat_verifications: List[BeatVerification] = Field(default=[])
