"""
Verifier Node - Hybrid Fact Checking & Source Mapping

Architecture:
    Phase 1: Lightweight Verification (fact_references 기반)
    Phase 2: Suspicious Beat Detection (숫자/통계 감지)
    Phase 3: Semantic Distortion Detection (LLM 의미 대조)
"""

import logging
import re
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from dotenv import load_dotenv
load_dotenv()

from src.script_gen.schemas.writer import Script
from src.script_gen.schemas.verifier import (
    VerifierOutput, VerificationReport, BeatVerification,
    SourceMapEntry, SourceInfo, FactReference,
    VerificationIssue, VerificationAction
)

logger = logging.getLogger(__name__)


async def verifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifier Node: 팩트 체크 & 출처 정리
    
    Input (from state):
        - script_draft: Writer의 결과
        - news_data: News Research의 결과 (facts)
    
    Output (to state):
        - verifier_output: VerifierOutput 객체
    """
    logger.info("Verifier Node 시작")
    
    # Fan-in Guard: script_draft가 비어있으면 skip (Writer가 skip한 경우)
    script_draft = state.get("script_draft", {})
    if not script_draft.get("script"):
        logger.info("Verifier: 스크립트 없음, skip")
        return {}
    script = Script(**script_draft.get("script", {}))
    news_data = state.get("news_data", {})
    facts = news_data.get("structured_facts", [])
    articles = news_data.get("articles", [])
    
    # Phase 1: Lightweight Verification
    logger.info("Phase 1: Lightweight Verification 시작")
    beat_verifications = _lightweight_verify(script, facts)
    
    # Phase 2: Suspicious Beat Detection
    logger.info("Phase 2: Suspicious Beat Detection 시작")
    suspicious_beats = _find_suspicious_beats(script, beat_verifications, facts)
    
    # Phase 3: Semantic Distortion Detection (LLM 의미 대조)
    logger.info("Phase 3: Semantic Distortion Detection 시작")
    await _detect_semantic_distortion(beat_verifications, facts)
    
    # Source Map 생성
    source_map = _build_source_map(beat_verifications, facts, articles)
    
    # Verification Report 생성
    report = _build_verification_report(beat_verifications, suspicious_beats)
    
    # VerifierOutput 생성
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
    beat_verifications: List[BeatVerification],
    facts: List[Dict]
) -> List[str]:
    """
    의심스러운 Beat 찾기 (Deep 검증 필요)
    """
    suspicious = []
    fact_map = {f.get("id"): f for f in facts}
    
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
        
        # 3. 숫자 교차검증 - 대본의 숫자가 인용 팩트에 실제 있는지
        if beat_ver.fact_references and _has_numbers(beat_ver.beat_text):
            ref_fact_contents = []
            for fr in beat_ver.fact_references:
                fact = fact_map.get(fr.fact_id)
                if fact:
                    ref_fact_contents.append(fact.get("content", ""))
            
            unmatched = _find_unmatched_numbers(beat_ver.beat_text, ref_fact_contents)
            if unmatched:
                beat_ver.issues.append(VerificationIssue(
                    beat_id=beat_ver.beat_id,
                    issue_type="unverified_number",
                    description=f"출처에 없는 수치 사용: {', '.join(unmatched)}",
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


def _find_unmatched_numbers(beat_text: str, fact_contents: List[str]) -> List[str]:

    """
    대본 문장의 숫자+단위가 인용 팩트 원문에 없으면 반환.
    할루시네이션 수치 탐지용.
    """
    patterns = [
        r'\d[\d,\.]*\s*%',
        r'\d[\d,\.]*\s*억',
        r'\d[\d,\.]*\s*만',
        r'\d[\d,\.]*\s*조',
        r'\d[\d,\.]*\s*배',
        r'\d[\d,\.]*\s*달러',
        r'\d[\d,\.]*\s*원',
        r'\d[\d,\.]*\s*명',
    ]
    
    unmatched = []
    all_fact_text = " ".join(fact_contents)
    
    for pattern in patterns:
        matches = re.findall(pattern, beat_text)
        for match in matches:
            # 핵심 숫자 추출 (단위/공백 제거)
            core_num = re.findall(r'[\d,\.]+', match)[0].replace(',', '')
            # 1자리 숫자는 무시 ("2배" 등 흔한 표현)
            if len(core_num.replace('.', '')) < 2:
                continue
            # 팩트 원문에 해당 숫자가 있는지 확인
            if core_num not in all_fact_text:
                unmatched.append(match.strip())
    
    return list(set(unmatched))


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
# Phase 3: Semantic Distortion Detection (LLM 의미 대조)
# =============================================================================

class _SemanticCheckResult(BaseModel):
    """LLM 의미 대조 결과 (내부용)"""
    is_distorted: bool = Field(description="Beat이 팩트 원문의 의미를 왜곡했는지")
    distortion_type: Optional[str] = Field(description="왜곡 유형: 확대, 축소, 날조, 맥락이탈", default=None)
    explanation: str = Field(description="판정 이유 (1-2문장)")


async def _detect_semantic_distortion(
    beat_verifications: List[BeatVerification],
    facts: List[Dict]
) -> None:
    """
    fact_references가 있는 Beat에 대해, Beat 텍스트와 팩트 원문을 LLM으로 비교.
    의미 왜곡이 감지되면 해당 Beat에 이슈를 추가한다.
    
    비용 최적화: fact_references가 있는 Beat만 검증 (보통 전체의 30-50%)
    """
    fact_map = {f.get("id"): f for f in facts}
    
    # fact_references가 있는 Beat만 필터
    beats_to_check = [
        bv for bv in beat_verifications
        if bv.fact_references and len(bv.fact_references) > 0
    ]
    
    if not beats_to_check:
        logger.info("Phase 3: 검증 대상 Beat 없음 (fact_references 없음)")
        return
    
    logger.info(f"Phase 3: {len(beats_to_check)}개 Beat 의미 대조 검증")
    
    # 병렬 검증 (최대 5개씩 배치)
    BATCH_SIZE = 5
    for i in range(0, len(beats_to_check), BATCH_SIZE):
        batch = beats_to_check[i:i + BATCH_SIZE]
        tasks = [
            _check_single_beat_semantic(bv, fact_map)
            for bv in batch
        ]
        await asyncio.gather(*tasks)


async def _check_single_beat_semantic(
    beat_ver: BeatVerification,
    fact_map: Dict[str, Dict]
) -> None:
    """
    단일 Beat에 대한 의미 대조 검증.
    왜곡이 감지되면 beat_ver.issues에 직접 추가.
    """
    # 인용된 팩트 원문 수집
    fact_texts = []
    for fr in beat_ver.fact_references:
        fact = fact_map.get(fr.fact_id)
        if fact:
            fact_texts.append(f"[{fr.fact_id}] {fact.get('content', '')}")
    
    if not fact_texts:
        return
    
    facts_str = "\n".join(fact_texts)
    
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        structured_llm = llm.with_structured_output(_SemanticCheckResult)
        
        result = await structured_llm.ainvoke([
            SystemMessage(content=(
                "당신은 팩트체커입니다. 대본 문장이 인용된 팩트 원문의 의미를 충실히 반영하는지 검증하세요.\n\n"
                "왜곡 판정 기준:\n"
                "- 확대: 팩트보다 범위나 의미를 키움 (예: '연구' → '산업 전체 변혁')\n"
                "- 축소: 중요한 맥락이나 조건을 빠뜨려 의미가 달라짐\n"
                "- 날조: 팩트에 없는 키워드/개념을 추가 (예: '방어책 연구' → '국방 통합')\n"
                "- 맥락이탈: 팩트의 맥락과 다른 맥락에서 사용\n\n"
                "자연스러운 서술을 위한 가벼운 표현 변경(의역)은 왜곡이 아닙니다.\n"
                "핵심 의미가 바뀌었는지만 판단하세요."
            )),
            HumanMessage(content=(
                f"## 대본 문장\n{beat_ver.beat_text}\n\n"
                f"## 인용된 팩트 원문\n{facts_str}\n\n"
                "이 대본 문장이 인용된 팩트의 의미를 왜곡했는지 판정하세요."
            ))
        ])
        
        if result.is_distorted:
            beat_ver.issues.append(VerificationIssue(
                beat_id=beat_ver.beat_id,
                issue_type="semantic_distortion",
                description=f"[{result.distortion_type}] {result.explanation}",
                severity="critical",
                suggested_action=VerificationAction.SOFTEN
            ))
            beat_ver.verified = False
            logger.warning(
                f"Phase 3 왜곡 감지 [{beat_ver.beat_id}]: "
                f"{result.distortion_type} - {result.explanation}"
            )
    
    except Exception as e:
        logger.warning(f"Phase 3 의미 대조 실패 [{beat_ver.beat_id}]: {e}")


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
