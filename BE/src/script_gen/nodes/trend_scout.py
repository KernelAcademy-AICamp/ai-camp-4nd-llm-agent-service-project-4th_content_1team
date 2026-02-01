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
    final_keywords = _filter_and_extract_keywords(raw_posts, channel_profile)
    
    # [결과 반환]
    # 키워드와 트렌드 분석 데이터를 반환
    # topic: Planner가 사용할 메인 주제 (1순위 키워드 자동 선택)
    selected_topic = final_keywords[0] if final_keywords else "Latest Tech Trends"
    if final_keywords:
        logger.info(f"선정된 키워드: {final_keywords}")
    
    return {
        "topic": selected_topic,
        "trend_analysis": {
            "keywords": final_keywords,
            "raw_posts": raw_posts, # 댓글 번역본 포함된 포스트 데이터
            "top_comments": [c for p in raw_posts for c in p.get("top_comments", [])] # 전체 댓글 풀 모음 (필요 시)
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
                    "permalink": post.get("permalink"),
                    # 텍스트가 너무 길면 자름
                    "selftext": post.get("selftext", "")[:300]
                })
                
        except Exception as e:
            logger.warning(f"에러 발생 r/{sub}: {e}")
            
    # 전체에서 Score 순으로 정렬 후 상위 5개만 남김
    all_posts.sort(key=lambda x: x["score"], reverse=True)
    top_posts = all_posts[:5]  # 상위 5개만 집중 분석

    # [제목 번역 추가] 상위 5개 포스트의 제목을 한국어로 번역
    try:
        import os
        if os.getenv("OPENAI_API_KEY"):
            llm_trans = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
            
            # 제목 리스트 추출
            titles = [p["title"] for p in top_posts]
            titles_str = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])
            
            title_prompt = f"""
            Translate the following {len(titles)} Reddit titles into natural Korean.
            
            CRITICAL RULES:
            1. Keep technical terms, product names, and company names in English (e.g., "Sony", "DDR4", "Nvidia", "AI").
            2. Translate the rest into clear, natural Korean suitable for a news headline.
            3. Output must have exactly {len(titles)} lines. One input line = One output line.
            4. Return ONLY the translated lines.
            
            [Titles]
            {titles_str}
            """
            
            msg = HumanMessage(content=title_prompt)
            res = llm_trans.invoke([msg])
            translated_titles = [line for line in res.content.strip().split("\n") if line.strip()]
            
            # 1:1 매칭하여 제목 교체 (개수 안 맞으면 그냥 둠)
            if len(translated_titles) >= len(top_posts):
                for i, post in enumerate(top_posts):
                    # 번호(1. )가 붙어있을 수 있으니 제거 시도
                    clean_title = translated_titles[i].split(". ", 1)[-1].strip()
                    # 혹시 모를 1. 2. 제거가 안된 경우 대비
                    if clean_title[0].isdigit() and clean_title[1] == '.':
                         clean_title = clean_title.split(". ", 1)[-1].strip()
                    
                    post["original_title"] = post["title"] # 원문 백업
                    post["title"] = clean_title
                    logger.debug(f"제목 번역: {post['original_title']} -> {post['title']}")

    except Exception as e:
        logger.warning(f"제목 번역 실패: {e}")

    # [댓글 수집 추가] 상위 5개 포스트에 대해서만 상세 댓글 수집
    logger.info("상위 포스트 댓글 수집 시작...")
    for post in top_posts:
        try:
            # permalink를 이용해 댓글 JSON 요청
            # 예: /r/technology/comments/1ab2c3/title.json
            permalink = post.get("permalink")
            if not permalink:
                continue
                
            comment_url = f"https://www.reddit.com{permalink}.json?sort=top&limit=5"
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            
            time.sleep(1) # API 매너 딜레이
            
            c_res = requests.get(comment_url, headers=headers, timeout=10)
            if c_res.status_code == 200:
                c_data = c_res.json()
                # 댓글 데이터는 배열의 두 번째 요소에 있음
                if len(c_data) > 1:
                    comments_data = c_data[1].get("data", {}).get("children", [])
                    extracted_comments = []
                    extracted_comments_scores = []
                    
                    for c in comments_data:
                        c_body = c.get("data", {}).get("body")
                        c_score = c.get("data", {}).get("score", 0)
                        # 삭제된 댓글이나 내용 없는 것 제외
                        if c_body and c_body != "[deleted]" and c_body != "[removed]":
                            extracted_comments.append(c_body) # 텍스트만 저장
                            extracted_comments_scores.append(c_score) # 점수 따로 저장
                    
                    # [번역] 추출된 댓글이 있으면 한국어로 번역 (GPT-4o-mini)
                    if extracted_comments:
                        try:
                            # 5개만 추림
                            target_comments = extracted_comments[:5]
                            target_scores = extracted_comments_scores[:5]
                            
                            import os
                            if os.getenv("OPENAI_API_KEY"):
                                llm_trans = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
                                comments_str = "\n".join([f"{i+1}. {c}" for i, c in enumerate(target_comments)])
                                
                                trans_prompt = f"""
                                Translate the following {len(target_comments)} Reddit comments into natural Korean (informal community style).
                                Handle slang and idioms appropriately.
                                
                                IMPORTANT: 
                                - Output must have exactly {len(target_comments)} lines.
                                - Do NOT merge lines. One input line = One output line.
                                - Return ONLY the translated lines.
                                
                                [Comments]
                                {comments_str}
                                """
                                
                                msg = HumanMessage(content=trans_prompt)
                                trans_res = llm_trans.invoke([msg])
                                translated_list = [line for line in trans_res.content.strip().split("\n") if line.strip()]
                                
                                final_comments = []
                                # 개수가 달라도 번역된 내용이 있으면 최대한 사용
                                if translated_list:
                                    for i in range(len(target_comments)):
                                        score_str = f" (👍{target_scores[i]})"
                                        if i < len(translated_list):
                                            # 번역문 + 스코어
                                            final_comments.append(translated_list[i].strip() + score_str)
                                        else:
                                            # 번역 모자라면 원문 + 스코어
                                            final_comments.append(target_comments[i] + score_str)
                                    
                                    post["top_comments"] = final_comments
                                else:
                                    # 번역 실패 시 원문 + 스코어
                                    post["top_comments"] = [f"{c} (👍{s})" for c, s in zip(target_comments, target_scores)]
                            else:
                                # API 키 없을 때 원문 + 스코어
                                post["top_comments"] = [f"{c} (👍{s})" for c, s in zip(target_comments, target_scores)]
                                
                        except Exception as e:
                            logger.warning(f"댓글 번역 실패: {e}")
                            # 에러 시 fallback
                            post["top_comments"] = [f"{c} (👍{s})" for c, s in zip(extracted_comments[:5], extracted_comments_scores[:5])]
                    else:
                        post["top_comments"] = []

                    logger.debug(f"댓글 수집 및 번역 완료: {post['title'][:20]}... ({len(post['top_comments'])}개)")
                    
        except Exception as e:
            logger.warning(f"댓글 수집 중 에러: {e}")
            post["top_comments"] = []


    return top_posts


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
