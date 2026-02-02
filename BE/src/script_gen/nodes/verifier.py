"""
Verifier Node - Hybrid Fact Checking & Source Mapping

Architecture:
    Phase 1: Lightweight Verification (fact_references 기반)
    Phase 2: Suspicious Beat Detection (숫자/통계 감지)
    Phase 3: Deep Verification (의심스러운 Beat만)
"""

import logging
import re
from typing import Dict, Any, List, Optional

from src.script_gen.schemas.writer import Script
from src.script_gen.schemas.verifier import (
    VerifierOutput, VerificationReport, BeatVerification,
    SourceMapEntry, SourceInfo, FactReference,
    VerificationIssue, VerificationAction
)

logger = logging.getLogger(__name__)


def verifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifier Node: 팩트 체크 & 출처 정리
    
    Input (from state):
        - script_draft: Writer의 결과
        - news_data: News Research의 결과 (facts)
    
    Output (to state):
        - verifier_output: VerifierOutput 객체
    """
    logger.info("Verifier Node 시작")
    
    # 1. 입력 데이터 추출
    script_draft = state.get("script_draft", {})
    script = Script(**script_draft.get("script", {}))
    news_data = state.get("news_data", {})
    facts = news_data.get("structured_facts", [])
    articles = news_data.get("articles", [])
    
    # 2. Phase 1: Lightweight Verification
    logger.info("Phase 1: Lightweight Verification 시작")
    beat_verifications = _lightweight_verify(script, facts)
    
    # 3. Phase 2: Suspicious Beat Detection
    logger.info("Phase 2: Suspicious Beat Detection 시작")
    suspicious_beats = _find_suspicious_beats(script, beat_verifications)
    
    # 4. Source Map 생성
    source_map = _build_source_map(beat_verifications, facts, articles)
    
    # 5. Verification Report 생성
    report = _build_verification_report(beat_verifications, suspicious_beats)
    
    # 6. VerifierOutput 생성
    verifier_output = VerifierOutput(
        verified=len(report.issues) == 0,
        source_map=source_map,
        verification_report=report,
        beat_verifications=beat_verifications
    )
    
    logger.info(f"Verifier 완료: {report.verified_beats}/{report.total_beats} Beats 검증 통과")
    logger.info(f"총 {len(report.issues)}개 이슈 발견")
    
    return {
        "verifier_output": verifier_output.model_dump()
    }


# =============================================================================
# Phase 1: Lightweight Verification
# =============================================================================

def _lightweight_verify(script: Script, facts: List[Dict]) -> List[BeatVerification]:
    """
    fact_references 기반 검증
    """
    beat_verifications = []
    
    # Fact ID → Fact 매핑 생성
    fact_map = {f.get("id"): f for f in facts}
    
    # 1. Hook 검증
    hook_verification = _verify_beat(
        beat_id="hook",
        beat_text=script.hook.text,
        fact_references_ids=getattr(script.hook, 'fact_references', []),
        fact_map=fact_map
    )
    beat_verifications.append(hook_verification)
    
    # 2. 각 Chapter의 Beat 검증
    for chapter in script.chapters:
        for beat in chapter.beats:
            beat_verification = _verify_beat(
                beat_id=beat.beat_id,
                beat_text=beat.line,
                fact_references_ids=getattr(beat, 'fact_references', []),
                fact_map=fact_map
            )
            beat_verifications.append(beat_verification)
    
    return beat_verifications


def _verify_beat(
    beat_id: str,
    beat_text: str,
    fact_references_ids: List[str],
    fact_map: Dict[str, Dict]
) -> BeatVerification:
    """
    개별 Beat 검증
    """
    fact_references = []
    issues = []
    
    for fact_id in fact_references_ids:
        # Fact ID가 실제 존재하는지 확인
        if fact_id not in fact_map:
            issues.append(VerificationIssue(
                beat_id=beat_id,
                issue_type="invalid_fact_id",
                description=f"Fact ID '{fact_id}'가 존재하지 않습니다",
                severity="critical",
                suggested_action=VerificationAction.DELETE
            ))
            continue
        
        # Fact 정보 추출
        fact = fact_map[fact_id]
        fact_ref = FactReference(
            fact_id=fact_id,
            fact_content=fact.get("content", "")[:100],
            category=fact.get("category", "unknown"),
            confidence=1.0  # Lightweight는 항상 1.0 (존재하면 OK)
        )
        fact_references.append(fact_ref)
    
    # 검증 통과 여부
    verified = len(issues) == 0
    
    return BeatVerification(
        beat_id=beat_id,
        beat_text=beat_text,
        fact_references=fact_references,
        issues=issues,
        verified=verified
    )


# =============================================================================
# Phase 2: Suspicious Beat Detection
# =============================================================================

def _find_suspicious_beats(
    script: Script,
    beat_verifications: List[BeatVerification]
) -> List[str]:
    """
    의심스러운 Beat 찾기 (Deep 검증 필요)
    """
    suspicious = []
    
    for beat_ver in beat_verifications:
        # 1. 숫자/통계가 있는데 fact_references 없음
        if _has_numbers(beat_ver.beat_text) and not beat_ver.fact_references:
            beat_ver.issues.append(VerificationIssue(
                beat_id=beat_ver.beat_id,
                issue_type="suspicious_claim",
                description="숫자/통계가 있지만 출처가 없습니다",
                severity="warning",
                suggested_action=VerificationAction.ADD_SOURCE
            ))
            suspicious.append(beat_ver.beat_id)
        
        # 2. Attribution phrase가 있는데 fact_references 없음
        if _has_attribution_phrase(beat_ver.beat_text) and not beat_ver.fact_references:
            beat_ver.issues.append(VerificationIssue(
                beat_id=beat_ver.beat_id,
                issue_type="suspicious_claim",
                description="출처 표현('~에 따르면')이 있지만 Fact 참조가 없습니다",
                severity="warning",
                suggested_action=VerificationAction.ADD_SOURCE
            ))
            suspicious.append(beat_ver.beat_id)
    
    return suspicious


def _has_numbers(text: str) -> bool:
    """텍스트에 숫자/통계가 있는지 확인"""
    # 패턴: 숫자 + % 또는 숫자 + 단위
    patterns = [
        r'\d+%',           # 40%
        r'\d+억',          # 10억
        r'\d+만',          # 100만
        r'\d+배',          # 2배
        r'\d+\.?\d*배',    # 1.5배
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False


def _has_attribution_phrase(text: str) -> bool:
    """출처 표현이 있는지 확인"""
    phrases = [
        "에 따르면",
        "에 의하면",
        "연구에서",
        "보고서에서",
        "발표했다",
        "밝혔다",
        "말했다",
        "according to",
        "research shows",
        "study found"
    ]
    
    for phrase in phrases:
        if phrase in text.lower():
            return True
    return False


# =============================================================================
# Source Map 생성
# =============================================================================

def _build_source_map(
    beat_verifications: List[BeatVerification],
    facts: List[Dict],
    articles: List[Dict]
) -> List[SourceMapEntry]:
    """
    출처 맵 생성
    """
    source_map = []
    
    # Article ID → Article 매핑
    article_map = {a.get("id"): a for a in articles}
    
    for beat_ver in beat_verifications:
        if not beat_ver.fact_references:
            continue
        
        sources = []
        for fact_ref in beat_ver.fact_references:
            # Fact에서 article_id 찾기
            fact = next((f for f in facts if f.get("id") == fact_ref.fact_id), None)
            if not fact:
                continue
            
            article_id = fact.get("article_id")
            article = article_map.get(article_id, {})
            
            source = SourceInfo(
                fact_id=fact_ref.fact_id,
                article_id=article_id,
                publisher=article.get("publisher", "Unknown"),
                published_date=article.get("published_date"),
                url=article.get("url"),
                snippet=fact.get("content", "")[:150]
            )
            sources.append(source)
        
        if sources:
            source_map.append(SourceMapEntry(
                beat_id=beat_ver.beat_id,
                sentence=beat_ver.beat_text[:100],
                sources=sources
            ))
    
    return source_map


# =============================================================================
# Verification Report 생성
# =============================================================================

def _build_verification_report(
    beat_verifications: List[BeatVerification],
    suspicious_beats: List[str]
) -> VerificationReport:
    """
    검증 리포트 생성
    """
    total_beats = len(beat_verifications)
    verified_beats = sum(1 for bv in beat_verifications if bv.verified)
    
    total_fact_refs = sum(len(bv.fact_references) for bv in beat_verifications)
    valid_fact_refs = sum(
        len([fr for fr in bv.fact_references if fr.confidence >= 0.8])
        for bv in beat_verifications
    )
    
    # 모든 이슈 수집
    all_issues = []
    for bv in beat_verifications:
        all_issues.extend(bv.issues)
    
    return VerificationReport(
        total_beats=total_beats,
        verified_beats=verified_beats,
        total_fact_references=total_fact_refs,
        valid_fact_references=valid_fact_refs,
        issues=all_issues,
        suspicious_beats=suspicious_beats
    )
