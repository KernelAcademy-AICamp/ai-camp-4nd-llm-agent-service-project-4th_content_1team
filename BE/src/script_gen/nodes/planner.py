"""
Planner Node - 콘텐츠 기획 에이전트
주제를 받아서 영상 구성안(ContentBrief)을 생성합니다.
재시도 로직을 통해 품질을 보장합니다.
"""
from typing import Dict, Any, Optional, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
import json
import logging
import re
import time
import asyncio

logger = logging.getLogger(__name__)

# 설정
MAX_RETRIES = 3  # 최대 재시도 횟수
OPENAI_MODEL = "gpt-4o-mini"


class ValidationError(Exception):
    """ContentBrief 검증 실패 시 발생하는 예외"""
    pass


async def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    주제와 채널 정보를 바탕으로 콘텐츠 기획안을 생성하는 노드
    재시도 로직을 통해 정확히 5개의 챕터를 보장합니다.
    
    Args:
        state: ScriptGenState (topic, channel_profile 포함)
    
    Returns:
        업데이트된 state (content_brief 추가됨)
    
    Raises:
        RuntimeError: MAX_RETRIES 번 시도해도 실패한 경우
    """
    
    # --- 1. 입력 데이터 추출 ---
    # state에서 topic과 channel_profile을 가져옴
    topic = state.get("topic")
    channel_profile = state.get("channel_profile", {})
    
    if not topic:
        raise ValueError("Topic is required in state")
    
    
    # --- 1.5. News RAG: 최신 뉴스 검색 ---
    # Planner 호출 전에 최근 뉴스를 가져와서 프롬프트에 포함
    logger.info(f"Fetching recent news for topic: {topic}")
    recent_news = await _fetch_recent_news(topic)
    logger.info(f"Found {len(recent_news)} recent news articles")
    
    
    # --- 2. 재시도 루프 ---
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Planner attempt {attempt + 1}/{MAX_RETRIES}")
            
            # --- 2-1. LLM 프롬프트 구성 ---
            # 첫 시도: 기본 프롬프트 (+ 최신 뉴스 포함)
            # 재시도: 이전 실패 이유를 포함한 피드백 프롬프트
            prompt = _build_planner_prompt(
                topic, 
                channel_profile, 
                attempt, 
                last_error,
                recent_news  # News RAG 결과 전달
            )
            
            
            # --- 2-2. LLM 호출 ---
            # ChatOpenAI 인스턴스 생성
            llm = ChatOpenAI(
                model=OPENAI_MODEL,
                temperature=0.4,  # 낮은 값: 일관된 JSON 형식 유지 (0.7→0.4)
            )
            response = await llm.ainvoke(prompt)
            
            
            # --- 2-3. 응답 파싱 ---
            # LLM이 반환한 텍스트를 JSON으로 파싱
            content_brief = _parse_llm_response(response.content)
            
            
            # --- 2-4. 엄격한 검증 ---
            # 필수 조건을 모두 만족하는지 확인
            # 하나라도 틀리면 ValidationError 발생
            _validate_content_brief(content_brief)
            
            
            # --- 2-5. 성공! State 업데이트 ---
            logger.info("✅ Planner success: Content brief generated")
            
            # search_keywords → search_queries (yt_fetcher용)
            topic_context = state.get("channel_profile", {}).get("topic_context", {})
            search_keywords = topic_context.get("search_keywords", []) if topic_context else []
            if search_keywords:
                content_brief["search_queries"] = search_keywords
            
            return {"content_brief": content_brief}
            
        
        except ValidationError as e:
            # 검증 실패 → 재시도
            last_error = str(e)
            logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
            
            if attempt == MAX_RETRIES - 1:
                # 마지막 시도도 실패 → 사용자 친화적 에러 메시지
                raise RuntimeError(
                    f"콘텐츠 기획안 생성에 실패했습니다. "
                    f"주제를 다시 확인하거나 잠시 후 시도해주세요. (오류: {e})"
                )
            
            # Exponential backoff (1초, 2초, 4초)
            wait_time = 2 ** attempt
            logger.info(f"Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
            continue
        
        except json.JSONDecodeError as e:
            # JSON 파싱 실패 → 재시도
            last_error = f"JSON parse error: {str(e)}"
            logger.warning(f"⚠️ JSON parsing failed: {e}")
            
            if attempt == MAX_RETRIES - 1:
                raise RuntimeError(
                    f"콘텐츠 기획안 생성에 실패했습니다. "
                    f"LLM이 올바른 형식으로 응답하지 않았습니다. 잠시 후 다시 시도해주세요."
                )
            
            # Exponential backoff
            wait_time = 2 ** attempt
            logger.info(f"Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
            continue
    
    # 여기까지 오면 안 됨 (위에서 return 또는 raise 했어야 함)
    raise RuntimeError("Unexpected error in planner_node")


# --- 헬퍼 함수들 ---

async def _fetch_recent_news(topic: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    주제와 관련된 최신 뉴스를 검색하는 함수 (News RAG)
    
    Args:
        topic: 검색할 주제
        max_results: 가져올 뉴스 개수 (기본 5개)
    
    Returns:
        뉴스 리스트 [{"title": "...", "snippet": "..."}]
    """
    try:
        # Tavily Search API 사용 (뉴스 검색에 최적화)
        search = TavilySearchResults(
            max_results=max_results,
            search_depth="basic",  # 빠른 검색
            include_domains=[],  # 모든 도메인 허용
            exclude_domains=[],
        )
        
        # 검색 쿼리 실행
        results = await search.ainvoke(f"{topic} 최신 뉴스")
        
        # 결과 포맷팅
        news_list = []
        for result in results:
            news_list.append({
                "title": result.get("title", ""),
                "snippet": result.get("content", "")[:200]  # 200자로 제한
            })
        
        return news_list
    
    except Exception as e:
        # 뉴스 검색 실패해도 Planner는 계속 진행
        logger.warning(f"Failed to fetch news: {e}. Continuing without news context.")
        return []


def _build_planner_prompt(
    topic: str, 
    channel_profile: Dict, 
    attempt: int = 0,
    last_error: Optional[str] = None,
    recent_news: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Planner용 프롬프트를 생성하는 헬퍼 함수
    레이아웃: 기본 정보 -> 뉴스 RAG -> 주제 컨텍스트(AI 추천) -> 개인화
    """
    
    # --- 기본 프롬프트 (영어로 작성) ---
    category = channel_profile.get("category", "general")
    target_audience = channel_profile.get("target_audience", "general viewers")
    channel_name = channel_profile.get("name", "Unknown Channel")
    
    # 확장 프로필
    average_duration = channel_profile.get("average_duration")
    content_style = channel_profile.get("content_style")
    one_liner = channel_profile.get("one_liner")
    persona_summary = channel_profile.get("persona_summary")
    main_topics = channel_profile.get("main_topics", [])
    hit_topics = channel_profile.get("hit_topics", [])
    audience_needs = channel_profile.get("audience_needs")
    
    # [News RAG] 최신 뉴스 컨텍스트
    news_context = ""
    if recent_news and len(recent_news) > 0:
        news_context = "\n\n**Recent News Context** (Use this for factual accuracy):\n"
        for i, news in enumerate(recent_news, 1):
            news_context += f"{i}. {news['title']}\n   {news['snippet']}\n"

    # [Topic Context] AI 추천 주제 컨텍스트 (NEW!)
    topic_context = ""
    topic_context_data = channel_profile.get("topic_context")  # API에서 전달
    if topic_context_data:
        topic_context = "\n\n**AI RECOMMENDATION CONTEXT** (Why this topic was recommended):\n"
        
        if topic_context_data.get('based_on_topic'):
            topic_context += f"- Based On Trend: {topic_context_data.get('based_on_topic')}\n"
        
        topic_context += f"- Trend Basis: {topic_context_data.get('trend_basis', '')}\n"
        topic_context += f"- Urgency: {topic_context_data.get('urgency', 'normal').upper()}\n"
        
        if topic_context_data.get('content_angles'):
            topic_context += "- Suggested Angles:\n"
            for angle in topic_context_data.get('content_angles', []):
                topic_context += f"  • {angle}\n"
        
        if topic_context_data.get('recommendation_reason'):
            topic_context += f"- Why This Fits Your Channel: {topic_context_data.get('recommendation_reason')}\n"
        
        # channel_topics/trend_topics에서 가져온 검색 키워드 (참고용, newsQuery는 구조에서 역산)
        if topic_context_data.get('search_keywords'):
            topic_context += "- Pre-researched Keywords (Reference only):\n"
            for kw in topic_context_data.get('search_keywords', []):
                topic_context += f"  • {kw}\n"
    
    # [Trend Scout] 커뮤니티 반응 컨텍스트 (주석처리됨, 향후 사용 가능)
    # trend_context = ""
    # if trend_analysis:
    #     trend_context = "\n\n**COMMUNITY REACTIONS (Trend Scout)**:\n"
    #     if "keywords" in trend_analysis:
    #         trend_context += f"- Hot Keywords: {', '.join(trend_analysis['keywords'])}\n"
    #     if "sentiment_summary" in trend_analysis:
    #         trend_context += f"- Overall Sentiment: {trend_analysis['sentiment_summary']}\n"
    #     if "top_comments" in trend_analysis and len(trend_analysis["top_comments"]) > 0:
    #         trend_context += "- Key Comments/Reactions:\n"
    #         for i, comment in enumerate(trend_analysis["top_comments"][:3], 1):
    #             trend_context += f"  {i}. {comment}\n"
    
    # [Personalization] 채널 맞춤 (확장됨!)
    personalization_context = "\n\n**Channel Personalization**:\n"
    personalization_context += f"- Channel Name: {channel_name}\n"
    
    if one_liner:
        personalization_context += f"- Channel Identity: {one_liner}\n"
    
    if persona_summary:
        personalization_context += f"- Persona Summary: {persona_summary}\n"
    
    if main_topics:
        personalization_context += f"- Main Topics: {', '.join(main_topics)}\n"
    
    if hit_topics:
        personalization_context += f"- Past Hit Topics: {', '.join(hit_topics)}\n"
    
    if average_duration:
        personalization_context += f"- Average Video Length: {average_duration} mins\n"
    
    if content_style:
        personalization_context += f"- Content Style: {content_style}\n"
    
    if audience_needs:
        personalization_context += f"- Audience Needs: {audience_needs}\n"
    
    differentiator = channel_profile.get("differentiator")
    if differentiator:
        personalization_context += f"- Differentiator: {differentiator}\n"
    
    title_patterns = channel_profile.get("title_patterns", [])
    if title_patterns:
        personalization_context += f"- Proven Title Patterns: {', '.join(title_patterns)}\n"
    
    base_prompt = f"""You are an expert YouTube content planner specializing in high-engagement videos.

**Topic**: {topic}
**Channel Category**: {category}
**Target Audience**: {target_audience}
**Language**: Korean (ALL output must be in Korean)

{news_context}{topic_context}{personalization_context}

**STRATEGIC INSTRUCTION — MANDATORY THINKING ORDER (Follow this EXACTLY)**:

**STEP 1: Determine Video Type** (MUST do this FIRST)
   - Analyze the Topic, AI Recommendation Context, and Channel Personalization together
   - Classify: 비교형(comparison) / 정보형(informational) / 주장형(opinion) / 리뷰형(review) / 전망형(forecast) / 복합형(hybrid)
   - Use Trend Basis, Suggested Angles, and Recommendation Reason to decide
   - Respect Urgency level (URGENT = focus on timeliness, NORMAL = evergreen approach)

**STEP 2: Design Chapter Structure** (Based on the video type from Step 1)
   - Design 5 chapters that fit the identified video type
   - If Past Hit Topics are provided, replicate successful formats
   - Match the Content Style and address Audience Needs
   - Each chapter must have a clear, distinct purpose aligned with the video type

**STEP 3: Reverse-Engineer newsQuery FROM the Structure** (CRITICAL)
   - For EACH chapter, ask: "What real-world data/articles do I need to write this chapter?"
   - newsQuery must be DERIVED from what each chapter needs, NOT from extracting words from the title
   - Include the topic title keywords too, but the primary source must be chapter needs
   - BAD example: title="AI 코딩 인터페이스" → newsQuery=["AI 코딩", "인터페이스"] (just extracting title words)
   - GOOD example: chapter goal="커서 vs 안티그래비티 비교" → newsQuery=["커서 안티그래비티 UI 비교 2026"]

4. **Fact + Opinion Structure**:
   - Don't just list facts. Use facts to back up a strong opinion or counter-intuitive insight.
   - Example: Instead of "Apple released Vision Pro", use "Why Vision Pro might FAIL (despite the specs)".

Create a comprehensive content brief for this video. You MUST respond with a valid JSON object following this exact structure:

{{
  "workingTitleCandidates": [
    {{"title": "엔비디아 독점 끝났다? AI 칩 전쟁의 진실", "angle": "반박"}},
    {{"title": "AI 반도체 시장 10배 성장, 지금 알아야 할 3가지", "angle": "긴급성"}},
    {{"title": "삼성 vs 엔비디아, AI 칩 대결의 승자는?", "angle": "비교"}}
  ],
  "coreQuestions": [
    "AI 반도체 시장은 왜 급성장하는가?",
    "엔비디아 독점 구조는 언제까지 유지될까?",
    "한국 기업들은 어떻게 대응해야 하는가?"
  ],
  "narrative": {{
    "hookGoal": "첫 15초에 시청자를 사로잡을 핵심 질문 제시",
    "structure": ["Hook", "Problem", "Evidence", "Insight", "Action"],
    "chapters": [
      {{"id": "c1", "goal": "주제 소개 및 배경 설명", "expectedAssets": ["뉴스 기사 스크린샷"]}},
      {{"id": "c2", "goal": "현재 시장 상황 분석", "expectedAssets": ["시장 점유율 표", "성장률 그래프"]}},
      {{"id": "c3", "goal": "핵심 근거 및 데이터 제시", "expectedAssets": ["통계 차트", "비교 표"]}},
      {{"id": "c4", "goal": "전문가 의견 및 분석", "expectedAssets": ["인터뷰 캡처", "분석 자료"]}},
      {{"id": "c5", "goal": "결론 및 시사점 정리", "expectedAssets": ["요약 인포그래픽"]}}
    ]
  }},
  "researchPlan": {{
    "newsQuery": [
      "AI 반도체 시장 규모 2026",
      "엔비디아 독점 비판 논란",
      "삼성전자 AI 칩 개발 사례",
      "글로벌 AI 칩 시장 점유율 통계",
      "NPU Neural Processing Unit 뜻 설명",
      "2026년 AI 반도체 산업 전망"
    ],
    "competitorQuery": [
      "AI 반도체 쉽게 설명",
      "AI 칩 아키텍처 심층 분석",
      "엔비디아 vs AMD 논쟁",
      "삼성 AI 칩 vs 엔비디아 성능 비교"
    ],
    "freshnessDays": 60
  }}
}}

**CRITICAL REQUIREMENTS** (Why these numbers matter):
1. chapters = EXACTLY 5: 영상 길이 10~15분 최적화 (챕터당 2~3분)
2. newsQuery ≥ 6: 다양한 관점 확보 (기본/반대/사례/통계/정의/최신)
3. competitorQuery ≥ 4: 시청자 레벨별 대응 (초보/전문가/논쟁/비교)
4. workingTitleCandidates: 3-5개 (선택지 제공)
5. ALL Korean output: 시청자가 한국어 사용자이므로
6. freshnessDays: 주제의 시의성에 따라 스마트하게 결정
   - 속보/루머/신제품: 7-14일 (매우 최신 정보 필요)
   - 트렌드/시장 분석: 30-60일 (최근 동향 필요)
   - 역사/개념/기술 설명: 180-365일 (시간 제약 적음)

**Example Output** (for reference, adapt to your topic):
Topic: "AI 반도체 시장 동향"
{{
  "workingTitleCandidates": [
    {{"title": "엔비디아 독점 끝났다? AI 칩 전쟁의 진실", "angle": "반박"}}
  ],
  "coreQuestions": ["AI 반도체 시장은 왜 급성장하는가?"],
  "narrative": {{
    "hookGoal": "첫 15초에 시청자를 사로잡을 핵심 질문 제시",
    "chapters": [
      {{"id": "c1", "goal": "주제 소개 및 배경 설명", "expectedAssets": ["뉴스 기사 스크린샷"]}}
    ]
  }},
  "researchPlan": {{
    "newsQuery": ["AI 반도체 시장 규모 2026", "엔비디아 독점 비판 논란", ...],
    "competitorQuery": ["AI 반도체 쉽게 설명", ...]
  }}
}}

Now generate the content brief for: {topic}
Respond ONLY with the JSON object, no additional text:

Generate the content brief now:"""

    # --- 재시도 시 피드백 추가 ---
    if attempt > 0 and last_error:
        feedback_prompt = f"""
[RETRY ATTEMPT {attempt + 1}]
Your previous response had an error: {last_error}

Please fix the issue and regenerate the content brief. Remember:
- chapters: EXACTLY 5 items (count them!)
- newsQuery: MINIMUM 6 items
- competitorQuery: MINIMUM 4 items
- Valid JSON format only

{base_prompt}"""
        return feedback_prompt
    
    return base_prompt


def _parse_llm_response(response_text: str) -> Dict:
    """
    LLM 응답에서 JSON을 추출하고 파싱하는 함수
    여러 패턴을 시도하여 안정성을 높입니다.
    
    Args:
        response_text: LLM이 반환한 텍스트
    
    Returns:
        파싱된 JSON (Dict)
    
    Raises:
        json.JSONDecodeError: JSON 파싱 실패 시
    """
    
    # 전략 1: 코드 블록 (```json ... ```) 찾기
    code_block_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response_text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass  # 다음 전략 시도
    
    # 전략 2: 첫 번째 완전한 JSON 객체 찾기 (비탐욕적)
    # 중괄호 균형을 맞춰서 찾음
    brace_count = 0
    start_idx = response_text.find('{')
    
    if start_idx != -1:
        for i in range(start_idx, len(response_text)):
            if response_text[i] == '{':
                brace_count += 1
            elif response_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    # 완전한 JSON 객체 발견
                    json_str = response_text[start_idx:i+1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        break  # 다음 전략 시도
    
    # 전략 3: 전체 텍스트를 파싱 시도 (공백 제거)
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        # 모든 전략 실패
        logger.error(f"Failed to parse JSON from response: {response_text[:200]}...")
        raise json.JSONDecodeError(
            f"Could not extract valid JSON from LLM response",
            response_text,
            0
        )


def _validate_content_brief(brief: Dict) -> None:
    """
    ContentBrief가 유효한지 검증하는 함수
    문제가 있으면 ValidationError를 발생시킵니다.
    
    Args:
        brief: 파싱된 ContentBrief JSON
    
    Raises:
        ValidationError: 검증 실패 시
    """
    
    # --- 1. 필수 필드 존재 확인 ---
    required_fields = ["workingTitleCandidates", "coreQuestions", "narrative", "researchPlan"]
    for field in required_fields:
        if field not in brief:
            raise ValidationError(f"Missing required field: {field}")
    
    
    # --- 2. workingTitleCandidates 검증 ---
    titles = brief.get("workingTitleCandidates", [])
    if not isinstance(titles, list) or len(titles) < 3:
        raise ValidationError(f"workingTitleCandidates must have at least 3 items (got {len(titles)})")
    
    
    # --- 3. chapters 검증 (가장 중요!) ---
    chapters = brief.get("narrative", {}).get("chapters", [])
    if len(chapters) != 5:
        raise ValidationError(
            f"chapters must have EXACTLY 5 items (got {len(chapters)})"
        )
    
    # 각 챕터의 내용 검증 (빈 챕터 방지)
    for i, chapter in enumerate(chapters, 1):
        if not isinstance(chapter, dict):
            raise ValidationError(f"Chapter {i} must be a dictionary")
        
        # goal 검증 (공백 방지)
        goal = chapter.get("goal", "").strip()
        if not goal:
            raise ValidationError(f"Chapter {i} has empty 'goal' field")
        if len(goal) < 5:
            raise ValidationError(f"Chapter {i} 'goal' too short (minimum 5 characters): '{goal}'")
        
        # expectedAssets 검증
        if not chapter.get("expectedAssets"):
            raise ValidationError(f"Chapter {i} missing 'expectedAssets' field")
        
        if not isinstance(chapter.get("expectedAssets"), list):
            raise ValidationError(f"Chapter {i} 'expectedAssets' must be a list")
        
        if len(chapter.get("expectedAssets", [])) == 0:
            raise ValidationError(f"Chapter {i} 'expectedAssets' cannot be empty")
    
    
    # --- 4. researchPlan 검증 ---
    research_plan = brief.get("researchPlan", {})
    news_query = research_plan.get("newsQuery", [])
    competitor_query = research_plan.get("competitorQuery", [])
    
    if len(news_query) < 6:
        raise ValidationError(f"newsQuery must have at least 6 items (got {len(news_query)})")
    
    if len(competitor_query) < 4:
        raise ValidationError(f"competitorQuery must have at least 4 items (got {len(competitor_query)})")
    
    
    # --- 5. 모든 검증 통과 ---
    # 에러가 없으면 아무것도 반환하지 않음 (None 반환)
