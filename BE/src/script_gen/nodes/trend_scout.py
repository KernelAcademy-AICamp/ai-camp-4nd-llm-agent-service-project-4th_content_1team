"""
Trend Scout Node - 레딧 트렌드 발굴 에이전트 (JSON 방식)
API 키 없이 레딧의 공개 JSON URL을 통해 최신 트렌드를 수집하고, 
채널 페르소나에 맞는 뉴스 검색 키워드를 추출합니다.
"""
from typing import Dict, Any, List, Optional
import logging
import requests
import random
import json
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# .env 로드
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# 브라우저 위장용 User-Agent 리스트 (429 차단 방지)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
]

def trend_scout_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    레딧에서 트렌드를 수집하고 뉴스 검색 쿼리를 생성하는 노드
    """
    logger.info("Trend Scout Node (JSON Mode) 시작")

    # 1. 입력 확인 & 타겟팅
    channel_profile = state.get("channel_profile", {})
    interests = channel_profile.get("topics", [])
    
    target_subreddits = _determine_subreddits(interests)
    logger.info(f"타겟 서브레딧: {target_subreddits}")

    # 2. 데이터 수집 (HTTP Requests)
    raw_posts = _fetch_reddit_json(target_subreddits)
    logger.info(f"수집된 포스트: {len(raw_posts)}개")

    # 수집 실패 시 안전장치 (Fallback)
    if not raw_posts:
        logger.warning("레딧 수집 실패 -> 기본 키워드 반환")
        fallback_keywords = ["최신 뉴스 트렌드", "글로벌 핫이슈", "IT 기술 동향"]
        if interests:
            fallback_keywords = [f"최신 {i} 뉴스" for i in interests]
        
        return {
            "researchPlan": {
                "newsQuery": fallback_keywords,
                "freshnessDays": 7
            }
        }

    # 3. LLM 필터링 및 키워드 추출
    selected_keywords = _filter_and_extract_keywords(raw_posts, channel_profile)
    logger.info(f"선정된 키워드: {selected_keywords}")

    # 4. State 업데이트
    return {
        "researchPlan": {
            "newsQuery": selected_keywords,
            "freshnessDays": 7 
        }
    }


def _determine_subreddits(interests: List[str]) -> List[str]:
    """관심사를 바탕으로 탐색할 서브레딧 결정"""
    # 기본값 (페르소나 없을 때)
    if not interests:
        return ["popular", "worldnews", "todayilearned"]
    
    # 간단한 키워드 매핑 (확장 가능)
    mapping = {
        "AI": ["artificial", "technology", "singularity"],
        "Tech": ["technology", "gadgets", "hardware"],
        "Finance": ["investing", "stocks", "economics"],
        "Game": ["gaming", "Games", "pcgaming"],
        "Korea": ["korea", "Hangukin"],
        "General": ["popular", "worldnews"]
    }
    
    targets = set()
    for interest in interests:
        # 매핑된 게 있으면 추가, 없으면 관심사 자체를 서브레딧으로 시도
        found = False
        for key, subs in mapping.items():
            if key.lower() in interest.lower():
                targets.update(subs)
                found = True
        if not found:
            targets.add(interest.replace(" ", "")) # 공백 제거 후 시도
            
    # 너무 많으면 3개만, 없으면 기본값
    result = list(targets)[:3]
    if not result:
        return ["popular", "technology"]
    return result


def _fetch_reddit_json(subreddits: List[str], limit_per_sub: int = 25) -> List[Dict]:
    """JSON URL을 통해 게시글 수집"""
    all_posts = []
    
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit_per_sub}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        
        try:
            # 429 방지를 위한 짧은 대기
            time.sleep(1) 
            
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                logger.warning(f"수집 실패 r/{sub}: Status {res.status_code}")
                continue
                
            data = res.json()
            children = data.get("data", {}).get("children", [])
            
            for child in children:
                post = child.get("data", {})
                
                # 광고(stickied)나 너무 인기 없는 글 제외
                if post.get("stickied") or post.get("score", 0) < 10:
                    continue
                    
                all_posts.append({
                    "title": post.get("title"),
                    "score": post.get("score"),
                    "num_comments": post.get("num_comments"),
                    "url": post.get("url"),
                    "subreddit": sub,
                    # 텍스트가 너무 길면 자름
                    "selftext": post.get("selftext", "")[:300]
                })
                
        except Exception as e:
            logger.warning(f"에러 발생 r/{sub}: {e}")
            
    # 전체에서 Score 순으로 정렬 후 상위 50개만 남김
    all_posts.sort(key=lambda x: x["score"], reverse=True)
    return all_posts[:50]


def _filter_and_extract_keywords(posts: List[Dict], persona: Dict) -> List[str]:
    """GPT-4o-mini를 사용하여 검색 키워드 추출"""
    
    # OpenAI 설정 확인
    import os
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OpenAI Key 없음 -> 상위 제목 반환")
        return [p["title"] for p in posts[:3]]

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    
    # 프롬프트 구성
    posts_text = ""
    for idx, p in enumerate(posts[:30]): # 상위 30개만 분석 대상
        posts_text += f"{idx+1}. [{p['subreddit']}] {p['title']} (Score: {p['score']}, Comments: {p['num_comments']})\n"

    # 페르소나 정보 포맷팅
    topics = persona.get("topics", ["General"])
    tone = persona.get("tone", "Informative")
    
    system_prompt = """
    You are a professional Content Researcher.
    Your goal is to select the BEST topics for a YouTube channel from the provided Reddit posts.
    
    CRITICAL INSTRUCTION:
    1. Select top 3-5 topics that match the Channel Persona.
    2. Convert them into **Korean Search Keywords** optimized for News Search (Naver/Google).
    3. Keywords must be **Noun-based** and **Factual**. (e.g., "Apple Vision Pro Release" -> "애플 비전 프로 출시")
    4. Exclude memes, personal rants, or vague videos. Focus on specific events, products, or issues.
    
    Return ONLY a Python list of strings. Example: ["keyword1", "keyword2"]
    """
    
    user_prompt = f"""
    [Channel Persona]
    - Topics: {topics}
    - Tone: {tone}

    [Reddit Hot Posts]
    {posts_text}

    Extract 5 best news search keywords (Korean):
    """

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        content = response.content.strip()
        
        # 파싱 시도 (리스트 형태)
        import ast
        if content.startswith("[") and content.endswith("]"):
            return ast.literal_eval(content)
        
        # 포맷 안 맞으면 줄바꿈으로 처리
        return [line.strip("- *\"'") for line in content.split("\n") if line.strip()]

    except Exception as e:
        logger.error(f"LLM 필터링 오류: {e}")
        # 오류 시 상위 글 제목 그냥 반환
        return [p["title"] for p in posts[:3]]
