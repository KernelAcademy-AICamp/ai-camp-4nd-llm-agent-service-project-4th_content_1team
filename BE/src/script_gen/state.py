"""
Script Generation State Definition
스크립트 생성 모듈의 공유 State 정의

Note: 이 파일은 graph.py의 실제 구현과 동기화되어 있습니다.
"""
from typing import TypedDict, Dict, Any, Optional


class ScriptGenState(TypedDict, total=False):
    """
    Script Generation 워크플로우의 공유 상태
    
    각 노드(Planner, News Research, Writer, Verifier 등)가
    이 State를 읽고 쓰면서 데이터를 주고받습니다.
    
    Workflow:
        User Input (topic + channel_profile)
        → Intent Analyzer (intent_analysis)
        → Planner (content_brief)
        → News Research (news_data) + YT Fetcher (youtube_data)
        → Competitor Analyzer (competitor_data)
        → Insight Builder (insight_pack)
        → Writer (script_draft)
        → Verifier (verifier_output)
    """
    
    # ==========================================================================
    # 1. 초기 입력 (Input)
    # ==========================================================================
    topic: str
    """사용자가 입력한 주제 (예: "AI 코딩 도구의 미래")"""
    
    topic_request_id: str
    """요청 ID (트래킹용)"""
    
    channel_profile: Dict[str, Any]
    """
    채널 정보 (build_planner_input에서 생성)
    
    필수 필드:
        - name: 채널명
        - category: 카테고리
        - target_audience: 타겟 청중
    
    권장 필드:
        - content_style: 콘텐츠 스타일
        - main_topics: 주요 주제 리스트
        - average_duration: 평균 영상 길이
        - one_liner: 채널 한 줄 정의
        - persona_summary: 페르소나 요약
        - hit_topics: 과거 인기 주제
        - audience_needs: 청중 니즈
    
    선택 필드 (AI 추천 시):
        - topic_context: AI 추천 컨텍스트
            - source: "ai_recommendation"
            - trend_basis: 트렌드 근거
            - urgency: 긴급도
            - content_angles: 콘텐츠 앵글
            - recommendation_reason: 추천 이유
    """
    
    # ==========================================================================
    # 1.5. Intent Analyzer 노드 결과 (Planner 이전)
    # ==========================================================================
    intent_analysis: Dict[str, Any]
    """
    독자 의도 분석 결과 (Intent Analyzer가 생성, Planner가 활용)

    구조:
        - core_question: 시청자가 진짜 원하는 핵심 질문
        - reader_pain_point: 시청자의 고민/불편함
        - reader_desire: 시청자가 원하는 결과
        - intent_mix: 의도 비율 {"informational": int, "emotional": int, "actionable": int}
        - content_angle: 콘텐츠 접근 각도
        - sub_topics: 다뤄야 할 하위 주제 [{"topic": str, "reason": str, "search_hint": str}]
    """

    # ==========================================================================
    # 2. Planner 노드 결과 (태윤)
    # ==========================================================================
    content_brief: Dict[str, Any]
    """
    콘텐츠 기획안
    
    Planner가 영상 유형 → 구조 설계 → 키워드 역산 순서로 생성.
    
    구조:
        - videoType: 영상 유형 (비교형/정보형/주장형/리뷰형/전망형/복합형)
        - workingTitleCandidates: 제목 후보 (3-5개)
        - coreQuestions: 핵심 질문
        - narrative: 내러티브 구조
            - hookGoal: 훅 전략
            - structure: 구조
            - chapters: 챕터 리스트 (정확히 5개)
        - researchPlan: 리서치 계획
            - newsQuery: 뉴스 검색 키워드 (6개 이상)
                ※ 챕터 구조에서 역산하여 생성됨 (제목 단어 추출 아님)
                ※ news_research_node가 이 키워드를 직접 사용함
            - competitorQuery: 경쟁사 검색 키워드 (4개 이상)
            - freshnessDays: 신선도 기준 (7-365일)
    """
    
    # ==========================================================================
    # 3. News Research 노드 결과 (태윤)
    # ==========================================================================
    news_data: Dict[str, Any]
    """
    뉴스 리서치 결과
    
    구조:
        - articles: 수집된 기사 리스트
            - id: 기사 ID (URL 해시)
            - title: 제목
            - url: URL
            - content: 본문
            - source: 출처
            - summary_short: 한 줄 요약
            - analysis: 분석 결과
                - facts: 팩트 리스트
                - opinions: 오피니언 리스트
            - images: 이미지 리스트
            - charts: 차트 리스트
        - structured_facts: 구조화된 팩트 (Fact Extractor 결과)
        - structured_opinions: 구조화된 오피니언
        - queries_used: 사용된 검색어
        - collected_at: 수집 시간
    """
    
    # ==========================================================================
    # 4. YouTube Fetcher + Competitor Analyzer 결과 (빛나)
    # ==========================================================================
    youtube_data: Dict[str, Any]
    """
    유튜브 영상 검색 결과
    
    구조:
        - videos: 검색된 영상 리스트
            - title: 제목
            - video_id: 영상 ID
            - views: 조회수
            - published_at: 게시일
    """
    
    competitor_data: Optional[Dict[str, Any]]
    """
    경쟁사 분석 결과
    
    구조:
        - top_videos: 상위 영상 분석
        - common_patterns: 공통 패턴
        - differentiation_opportunities: 차별화 기회
    """
    
    # ==========================================================================
    # 5. Insight Builder 결과
    # ==========================================================================
    insight_pack: Dict[str, Any]
    """
    전략 인사이트
    
    구조:
        - positioning: 포지셔닝 전략
        - differentiators: 차별화 요소
        - hook_plan: 훅 계획
        - story_structure: 스토리 구조
    """
    
    # ==========================================================================
    # 6. Writer 노드 결과 (빛나)
    # ==========================================================================
    script_draft: Dict[str, Any]
    """
    작성된 스크립트 초안
    
    구조:
        - script_draft_id: 스크립트 ID
        - script: 스크립트 본문
            - hook: 훅
            - chapters: 챕터 리스트
            - outro: 아웃트로
        - metadata: 메타데이터
    """
    
    # ==========================================================================
    # 7. Verifier 노드 결과 (태윤)
    # ==========================================================================
    verifier_output: Optional[Dict[str, Any]]
    """
    검증 결과
    
    구조:
        - sourceMap: 출처 매핑
        - removedClaims: 제거된 주장
        - warnings: 경고 사항
        - final_script: 최종 검증된 스크립트
    """
