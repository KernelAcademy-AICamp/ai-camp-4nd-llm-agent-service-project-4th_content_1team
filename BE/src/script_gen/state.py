"""
Script Generation State Definition
스크립트 생성 모듈의 공유 State 정의
"""
from typing import TypedDict, List, Dict, Any, Optional


class ScriptGenState(TypedDict, total=False):
    """
    Script Generation 워크플로우의 공유 상태
    
    각 노드(Planner, Researcher, Writer, Verifier 등)가
    이 State를 읽고 쓰면서 데이터를 주고받습니다.
    """
    
    # --- 1. 초기 입력 (Input) ---
    topic: str                      # 사용자가 입력한 주제 (예: "AI 반도체 시장 동향")
    channel_profile: Dict[str, Any] # 채널 정보
                                    # 필수: category, target_audience
                                    # 선택 (개인화): average_duration (분), content_style (리스트형/스토리형/튜토리얼형), 
                                    #               recent_feedback (댓글 피드백 리스트)
    
    # --- 2. Planner 노드 결과 (태윤) ---
    content_brief: Dict[str, Any]   # 기획안 (제목 후보, 챕터 구성, 리서치 계획)
                                    # 구조: workingTitleCandidates, coreQuestions, narrative, researchPlan
    
    # --- 3. News Researcher 노드 결과 (태윤) ---
    article_set: Dict[str, Any]     # 수집된 뉴스 기사 및 원문
                                    # 구조: articles (리스트), 각 article은 url, title, content, assets 포함
    
    # --- 4. Fact Extractor 노드 결과 (태윤) ---
    fact_set: Dict[str, Any]        # 구조화된 팩트 데이터
                                    # 구조: facts (리스트), insightSentences, visualPlan
    
    # --- 5. YouTube Fetcher 노드 결과 (빛나) ---
    youtube_data: Dict[str, Any]    # 경쟁 영상 분석 데이터
                                    # 구조: videos (리스트), 각 video는 title, views, analysis 포함
    
    # --- 6. Writer 노드 결과 (빛나) ---
    draft_script: str               # 작성된 스크립트 초안 (페르소나 적용 전/후)
    
    # --- 7. Verifier 노드 결과 (태윤) ---
    verification_report: Dict[str, Any]  # 팩트 체크 결과
                                         # 구조: sourceMap, removedClaims, warnings
    
    final_script: str               # 최종 검증 완료된 스크립트
