"""
News Research Node (Advanced) - 고성능 뉴스 및 시각 자료 수집기

[핵심 로직]
1. Deep Fetch: 검색어당 15개의 기사를 수집하여 후보군을 넓힘
2. Smart Dedup: 유사한 주제의 기사를 그룹핑하고, 각 그룹에서 '알짜 기사' 1개씩만 선별 (Top 3)
3. Aggressive Crawl: 페이지 내 100px 이상 모든 이미지를 수집 (규칙 기반 필터링 최소화)
4. AI Context Check: GPT-4o-mini가 기사 본문 요약과 이미지를 함께 분석하여 진짜 차트/표 발굴
"""
from typing import Dict, Any, List, Optional
import requests
import json
import trafilatura
import logging
import concurrent.futures
import os
import hashlib
import re
import uuid
from datetime import datetime
from playwright.sync_api import sync_playwright
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# .env 로드
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# 설정
CRAWL_TIMEOUT = 40
MAX_WORKERS = 3 
SIMILARITY_THRESHOLD = 0.6  # 제목 유사도 기준 (0.6 이상이면 같은 내용으로 간주)


def news_research_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """각 키워드당 제일 관련성 높은 기사 1개씩 검색합니다."""
    logger.info("News Research Node (Per-Keyword) 시작")

    # 1. 입력 데이터 - Planner의 research_plan 키워드 우선 사용
    content_brief = state.get("content_brief", {})
    research_plan = content_brief.get("researchPlan", {}) if content_brief else {}
    base_queries = research_plan.get("newsQuery", [])

    # fallback: Planner newsQuery가 없으면 기존 search_keywords 사용
    if not base_queries:
        channel_profile = state.get("channel_profile", {})
        topic_context = channel_profile.get("topic_context", {})
        base_queries = topic_context.get("search_keywords", []) if topic_context else []
        logger.info(f"검색 쿼리 (Fallback): {base_queries}")
    else:
        logger.info(f"검색 쿼리 (Planner 역산): {base_queries}")

    if not base_queries:
        return {"news_data": {"articles": []}}

    topic = state.get("topic", "")
    logger.info(f"키워드별 기사 검색 시작: {len(base_queries)}개 키워드 → 각 1개 기사")

    # 2. 각 키워드당 제일 관련성 높은 기사 1개씩 선택
    selected_articles = _fetch_one_per_keyword(base_queries, topic)
    logger.info(f"선택된 기사: {len(selected_articles)}개")

    # 3. 본문 및 이미지 정밀 크롤링 + AI 분석
    full_articles = _crawl_and_analyze(selected_articles, topic=topic)
    logger.info(f"크롤링 완료: {len(full_articles)}개 (선택 {len(selected_articles)}개 중)")

    # 크롤링에 실패한 기사는 Naver 기본 정보(제목/URL/설명)로 폴백
    crawled_urls = {art["url"] for art in full_articles}
    import hashlib
    for art in selected_articles:
        if art["url"] not in crawled_urls:
            logger.info(f"크롤링 실패 폴백: {art['title'][:40]}")
            full_articles.append({
                **art,
                "id": hashlib.md5(art["url"].encode()).hexdigest(),
                "summary_short": art.get("desc", ""),
                "summary": art.get("desc", ""),
                "analysis": {"facts": [], "opinions": []},
                "images": [],
                "charts": [],
            })

    # 4. 기사 정렬 (차트 있는 기사 우선)
    full_articles.sort(key=lambda x: (len(x.get("charts", [])), len(x.get("images", []))), reverse=True)

    # 5. [Fact Extractor] 기사별 확정 인덱스로 팩트 수집
    structured_facts = []
    for i, art in enumerate(full_articles):
        art_facts = art.get("analysis", {}).get("facts", [])
        source_name = _extract_source_from_url(art.get("url", "")) or art.get("source", "Unknown")
        article_id = art.get("id", "")
        article_url = art.get("url", "")
        for fact_text in art_facts:
            structured_facts.append({
                "id": f"fact-{uuid.uuid4().hex[:12]}",
                "content": fact_text,
                "source_index": i,
                "source_name": source_name,
                "source_indices": [i],
                "article_id": article_id,
                "article_url": article_url,
                "category": "Fact",
                "visual_proposal": "None",
            })
    logger.info(f"[Fact Extractor] 팩트 수집: {len(structured_facts)}개 (기사 {len(full_articles)}개)")

    # 6. Opinions 모음
    structured_opinions = []
    for art in full_articles:
        ops = art.get("analysis", {}).get("opinions", [])
        if ops:
            source = art.get("source", "Unknown")
            for op in ops:
                structured_opinions.append(f"[{source}] {op}")

    return {
        "news_data": {
            "articles": full_articles,
            "structured_facts": structured_facts,
            "structured_opinions": structured_opinions,
            "queries_used": base_queries,
            "collected_at": datetime.now().isoformat()
        }
    }


def _search_naver(endpoint: str, keyword: str, headers: dict, display: int = 10) -> List[Dict]:
    """
    Naver 검색 API 호출 공통 함수.
    endpoint: "blog", "news", "cafearticle" 등
    """
    url = f"https://openapi.naver.com/v1/search/{endpoint}.json"
    try:
        params = {"query": keyword, "display": display, "sort": "sim"}
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code != 200:
            logger.warning(f"Naver {endpoint} API 오류 ({keyword}): {res.status_code}")
            return []
        items = res.json().get("items", [])
        results = []
        for item in items:
            link = item.get("originallink") or item.get("link") or item.get("bloggerlink", "")
            if not link:
                continue
            clean_title = re.sub('<[^<]+?>', '', item.get("title", ""))
            clean_desc = re.sub('<[^<]+?>', '', item.get("description", ""))
            results.append({
                "title": clean_title,
                "url": link,
                "desc": clean_desc,
                "pub_date": item.get("pubDate") or item.get("postdate"),
                "query": keyword,
                "source": _extract_source_from_url(link),
                "_search_type": endpoint,
            })
        return results
    except Exception as e:
        logger.warning(f"Naver {endpoint} 검색 오류 ({keyword}): {e}")
        return []


def _fetch_one_per_keyword(keywords: List[str], topic: str) -> List[Dict]:
    """
    각 키워드당 제일 관련성 높은 기사/포스트 1개씩 선별합니다.

    검색 우선순위:
      1순위) Naver Blog  — 실사용 리뷰, 튜토리얼, 비교 글 (how-to 키워드에 최적)
      2순위) Naver News  — 언론사 기사 (업계 동향, 통계, 사건 중심)
    각 소스에서 GPT가 "관련없음" 판단 시 다음 소스로 넘어갑니다.
    """
    results = []
    seen_urls: set = set()

    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.error("NAVER API Key Missing")
        return []

    api_key = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0) if api_key else None

    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}

    for raw_keyword in keywords:
        # 쉼표로 이어진 복합 키워드를 분리하여 첫 번째 유효한 결과 사용
        sub_keywords = [k.strip() for k in raw_keyword.split(",") if k.strip()]
        if not sub_keywords:
            continue

        found = False
        for keyword in sub_keywords:
            if found:
                break

            # 1순위: Naver Blog (실사용 리뷰/튜토리얼 중심)
            blog_candidates = [
                c for c in _search_naver("blog", keyword, headers, display=10)
                if c["url"] not in seen_urls
            ]
            if blog_candidates:
                best = _pick_best_article(blog_candidates, keyword, topic, llm)
                if best:
                    seen_urls.add(best["url"])
                    results.append(best)
                    logger.info(f"키워드 '{keyword}' [블로그]: '{best['title'][:50]}' 선택")
                    found = True
                    continue
                else:
                    logger.info(f"키워드 '{keyword}' [블로그]: GPT 관련없음 판단 → 뉴스로 전환")

            # 2순위: Naver News (언론사 기사)
            news_candidates = [
                c for c in _search_naver("news", keyword, headers, display=10)
                if c["url"] not in seen_urls
            ]
            if news_candidates:
                best = _pick_best_article(news_candidates, keyword, topic, llm)
                if best:
                    seen_urls.add(best["url"])
                    results.append(best)
                    logger.info(f"키워드 '{keyword}' [뉴스]: '{best['title'][:50]}' 선택")
                    found = True
                    continue
                else:
                    logger.warning(f"키워드 '{keyword}' [뉴스]: GPT 관련없음 판단 → 기사 없음 처리")

    return results


def _pick_best_article(candidates: List[Dict], keyword: str, topic: str, llm) -> Optional[Dict]:
    """
    주어진 키워드와 영상 주제에 가장 관련성 높은 글 1개를 GPT로 선택합니다.
    모든 후보가 관련없다고 판단되면 None을 반환합니다 (거부 가능).
    """
    if not candidates:
        return None
    if not llm:
        return candidates[0]

    try:
        article_list = "\n".join(
            f"{i+1}. {art['title']} — {art['desc'][:150]}"
            for i, art in enumerate(candidates)
        )

        prompt = f"""유튜브 스크립트 리서치를 위해 가장 적합한 글 1개를 선택하세요.

[영상 주제]
"{topic}"

[검색 키워드]
"{keyword}"

[후보 글]
{article_list}

선택 기준:
- 검색 키워드 "{keyword}"의 핵심 내용을 직접 다루는 글
- 유튜브 스크립트에 인용할 수 있는 구체적인 수치, 사실, 사례, 사용 경험이 있는 글
- 실사용 리뷰, 튜토리얼, 비교 글 우선
- 광고성·홍보성 글 제외

⚠️ 중요: 후보 글 중 키워드 "{keyword}"와 직접 관련된 글이 하나도 없다면 반드시 "0"을 답하세요.
예를 들어 "Copilot 사용법" 키워드인데 도로공사나 주식 기사만 있다면 → 0

숫자만 응답하세요. 관련 없으면 0, 관련 있으면 해당 번호 (예: 3)"""

        response = llm.invoke(prompt)
        idx_str = response.content.strip()

        # 숫자만 추출
        digits = re.sub(r'[^\d]', '', idx_str)
        if digits:
            idx = int(digits) - 1
            if idx == -1:
                # GPT가 "0" 반환 = 관련없음 거부
                logger.info(f"기사 선택: GPT가 '{keyword}' 관련 글 없음 판단 → None 반환")
                return None
            if 0 <= idx < len(candidates):
                return candidates[idx]

        return None  # 파싱 실패 시도 None (불확실한 결과 포함 안 함)

    except Exception as e:
        logger.warning(f"기사 선택 실패 ({keyword}): {e} → None 반환")
        return None



# 도메인 → 언론사명 매핑
SOURCE_DOMAIN_MAP = {
    "chosun.com": "조선일보", "donga.com": "동아일보", "joongang.co.kr": "중앙일보",
    "hani.co.kr": "한겨레", "khan.co.kr": "경향신문", "kmib.co.kr": "국민일보",
    "seoul.co.kr": "서울신문", "munhwa.com": "문화일보", "segye.com": "세계일보",
    "mk.co.kr": "매일경제", "mt.co.kr": "머니투데이", "hankyung.com": "한국경제",
    "sedaily.com": "서울경제", "edaily.co.kr": "이데일리", "fnnews.com": "파이낸셜뉴스",
    "asiae.co.kr": "아시아경제", "etnews.com": "전자신문", "zdnet.co.kr": "ZDNet Korea",
    "bloter.net": "블로터", "ddaily.co.kr": "디지털데일리",
    "yna.co.kr": "연합뉴스", "yonhapnews.co.kr": "연합뉴스",
    "newsis.com": "뉴시스", "news1.kr": "뉴스1",
    "bbc.com": "BBC", "bbc.co.uk": "BBC",
    "reuters.com": "Reuters", "bloomberg.com": "Bloomberg",
    "nytimes.com": "NYT", "wsj.com": "WSJ",
    "techcrunch.com": "TechCrunch", "theverge.com": "The Verge",
    "cnbc.com": "CNBC", "ft.com": "FT",
    "fortunekorea.co.kr": "포춘코리아", "venturesquare.net": "벤처스퀘어",
    "newspim.com": "뉴스핌", "theinformation.com": "The Information",
    "inews24.com": "아이뉴스24", "zdnet.com": "ZDNet",
}

def _extract_source_from_url(url: str) -> str:
    """URL 도메인에서 출처명을 추출합니다."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # 공통 서브도메인 제거
        for prefix in ("www.", "view.", "news.", "m.", "mobile."):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]

        # 네이버 블로그/카페 특별 처리
        if "blog.naver.com" in domain or "blog.me" in domain:
            return "네이버 블로그"
        if "cafe.naver.com" in domain:
            return "네이버 카페"
        if "tistory.com" in domain:
            return "티스토리"
        if "velog.io" in domain:
            return "Velog"
        if "brunch.co.kr" in domain:
            return "브런치"

        # 정확한 매칭
        if domain in SOURCE_DOMAIN_MAP:
            return SOURCE_DOMAIN_MAP[domain]
        # 부분 매칭 (서브도메인 대응)
        for key, name in SOURCE_DOMAIN_MAP.items():
            if key in domain:
                return name
        return ""
    except Exception:
        return ""


import base64
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

class LegacySSLAdapter(HTTPAdapter):
    """오래된 서버(SSL Legacy Renegotiation) 접속을 위한 어댑터"""
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl.create_default_context()
        ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx
        )

import uuid

def download_image_to_local(image_url: str, referrer_url: str = None) -> Optional[str]:
    """
    이미지를 public/images/news 경로에 저장하고 상대 경로를 반환.
    실패 시 None 반환.
    """
    try:
        # BE 폴더 기준 절대 경로 생성 (현재 파일 위치 기준)
        be_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        save_dir = os.path.join(be_root, "public", "images", "news")
        os.makedirs(save_dir, exist_ok=True)

        session = requests.Session()
        session.mount('https://', LegacySSLAdapter())
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": referrer_url if referrer_url else ""
        }
        
        res = session.get(image_url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None
            
        ext = "jpg"
        if "png" in image_url.lower(): ext = "png"
        if "gif" in image_url.lower(): ext = "gif"
        
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join(save_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(res.content)
            
        return f"/images/news/{filename}"
    except Exception as e:
        logger.error(f"Image Download Failed: {e}")
        return None

import time

def _check_image_context(image_url: str, article_title: str, article_summary: str, referrer_url: str = None) -> Dict:
    """
    GPT-4o-mini에게 [기사 요약 + 이미지(Base64)]를 보여주고 판단하게 함
    (Legacy SSL 서버 지원 + Rate Limit 재시도 로직 추가)
    """
    max_retries = 3
    retry_delay = 2  # 초
    
    for attempt in range(max_retries):
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key: return {"relevant": False}
            
            # 1. 이미지 다운로드 (Legacy SSL 지원 Session 사용)
            session = requests.Session()
            session.mount('https://', LegacySSLAdapter())
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": referrer_url if referrer_url else ""
            }
            
            img_res = session.get(image_url, headers=headers, timeout=10)
            if img_res.status_code != 200:
                return {"relevant": False}
                
            # 2. Base64 인코딩
            encoded_string = base64.b64encode(img_res.content).decode("utf-8")
            data_url = f"data:image/jpeg;base64,{encoded_string}"
            
            llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
            
            prompt = f"""
            [분석 요청]
            기사 제목: {article_title}
            기사 요약: {article_summary}
            
            이 이미지를 분석해서 JSON으로 답해줘:
            1. relevant: 이 이미지가 기사와 관련이 있는가?
            2. type: "chart", "table", "photo", "other"
            3. description: 이미지 설명 (한글)
            
            판단 기준:
            - chart/table: 기사의 데이터/통계를 시각화한 차트, 그래프, 표
            - photo: 기사 주제와 직접 연관된 사진
              예) 부동산 기사 → 아파트/건물 사진 OK
              예) 스포츠 기사 → 선수/경기 사진 OK
              예) 경제 기사 → 관련 현장/인물 사진 OK
            - other: 광고, 로고, 배너, 아이콘 → relevant=false
            
            relevant=true 조건:
            - 차트/표는 무조건 포함
            - 사진은 기사 주제와 명확히 연관된 경우만 포함
            - 광고/로고/배너/기자 프로필 사진은 제외
            """
            
            msg = HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}}
            ])
            
            res = llm.invoke([msg])
            content = res.content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
            
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 지수 백오프
                    continue
            logger.warning(f"AI Check Error: {e}")
            return {"relevant": False}
    return {"relevant": False}


def _crawl_and_analyze(articles: List[Dict], topic: str = "") -> List[Dict]:
    """Playwright로 접속하여 본문 및 이미지를 싹 긁어오고 AI로 분석"""
    results = []
    
    if not articles:
        return []

    def process_one(item):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                
                # 🎭 봇 탐지 우회: User-Agent 변경
                page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                # 로딩 대기
                try:
                    page.goto(item["url"], timeout=CRAWL_TIMEOUT*1000, wait_until="domcontentloaded")
                    
                    # [Scroll Logic] Lazy Loading 이미지 로딩을 위해 스크롤 다운
                    for _ in range(5):
                        page.evaluate("window.scrollBy(0, document.body.scrollHeight / 5)")
                        page.wait_for_timeout(2000)  # 2.0초 대기 (Wait longer for lazy loading)
                        
                except:
                    browser.close()
                    return None
                
                # 본문 추출
                content_html = page.content()
                text = trafilatura.extract(content_html, include_links=False)
                if not text or len(text) < 50:
                    browser.close()
                    return None
                
                # [ID 생성] URL 해시 기반 고유 ID 부여 (Verifier 연결용)
                item["id"] = hashlib.md5(item["url"].encode()).hexdigest()

                # [출처명 자동 추출] og:site_name 메타태그에서 언론사명 가져오기
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content_html, "html.parser")
                    og_tag = soup.find("meta", property="og:site_name")
                    if og_tag and og_tag.get("content", "").strip():
                        item["og_source"] = og_tag["content"].strip()
                except Exception:
                    pass

                # 이미지 추출 (Lazy Loading 지원 + Aggressive Mode)
                # data-src, data-original, data-url 우선 확인
                images_found = []
                
                # [개선] 스마트 본문 영역 감지 알고리즘
                def find_article_body_smart(page):
                    """
                    휴리스틱 기반으로 본문 영역을 자동 감지
                    - 텍스트 밀도, 문단 개수, 이미지 등을 종합 평가
                    """
                    # 1단계: 기존 선택자 시도 (빠른 경로)
                    common_selectors = [
                        "article", 
                        ".article-body", ".article_body", 
                        "#articleBody", "#newsBody",
                        "div[itemprop='articleBody']",
                    ]
                    
                    for selector in common_selectors:
                        try:
                            elem = page.query_selector(selector)
                            if elem and len(elem.inner_text()) > 200:
                                logger.debug(f"[ARTICLE] 기존 선택자로 본문 발견: {selector}")
                                return elem
                        except:
                            continue
                    
                    # 2단계: 스마트 알고리즘 - 후보 요소 수집
                    logger.debug("[ARTICLE] 스마트 알고리즘으로 본문 탐색 시작")
                    candidates = page.query_selector_all('div, section, article')
                    
                    best_score = -999999
                    best_elem = None
                    
                    for elem in candidates:
                        try:
                            text = elem.inner_text()
                            text_len = len(text)
                            
                            # 너무 짧으면 스킵
                            if text_len < 200:
                                continue
                            
                            # 점수 계산 요소
                            p_count = len(elem.query_selector_all('p'))
                            li_count = len(elem.query_selector_all('li'))
                            img_count = len(elem.query_selector_all('img'))
                            link_count = len(elem.query_selector_all('a'))
                            
                            # 점수 = 텍스트 길이 + 문단 + 이미지 - 링크
                            score = (text_len * 0.3) + ((p_count + li_count) * 100) + (img_count * 50) - (link_count * 10)
                            
                            logger.debug(f"[ARTICLE] 후보: text={text_len}, p={p_count}, img={img_count}, link={link_count}, score={score:.0f}")
                            
                            if score > best_score:
                                best_score = score
                                best_elem = elem
                        except:
                            continue
                    
                    if best_elem:
                        logger.info(f"[ARTICLE] 스마트 알고리즘으로 본문 발견 (점수: {best_score:.0f})")
                        return best_elem
                    
                    # 3단계: 폴백 - body 전체
                    logger.warning("[ARTICLE] 본문 영역을 찾지 못함. body 전체 사용")
                    return page.query_selector('body')
                
                # 스마트 알고리즘으로 본문 영역 찾기
                article_area = find_article_body_smart(page)
                
                # 본문 영역을 찾았으면 그 안에서만, 못 찾았으면 전체 페이지에서 검색
                search_area = article_area if article_area else page
                
                # 1. img 태그
                imgs = search_area.query_selector_all("img")
                logger.debug(f"[ARTICLE] 검색 영역에서 발견한 img 태그: {len(imgs)}개")
                
                for img in imgs:
                    # Lazy Loading 속성 확인
                    src = None
                    for attr in ["data-src", "data-original", "data-url", "src"]:
                        val = img.get_attribute(attr)
                        if val and val.startswith("http"):
                            src = val
                            break
                    
                    if src:
                        # [Filter] 쓰레기 이미지 제거 (기자, 아이콘, 배너 등)
                        src_lower = src.lower()
                        trash_keywords = [
                            '.svg', '.gif', 'logo', 'icon', 'banner', 'ad', 'button', 'btn',
                            'reporter', 'profile', 'journalist', 'avatar'  # 기자/프로필 사진 필터 추가
                        ]
                        if any(x in src_lower for x in trash_keywords):
                            logger.debug(f"[FILTER] 키워드 차단: {src[:80]}")
                            continue
                            
                        # 크기 체크 (JS)
                        try:
                            w = img.evaluate("el => el.naturalWidth")
                            h = img.evaluate("el => el.naturalHeight")
                            
                            # [Filter] 크기 기준 상향 (50px -> 150px)
                            # 너무 작은 이미지는 정보가치가 없음
                            if w > 0 and w < 150 and h > 0 and h < 150:
                                logger.debug(f"[FILTER] 크기 차단: {src[:80]} ({w}x{h})")
                                continue
                                
                            # Lazy Loading 초기화 전이라 0일 수도 있음 -> 일단 URL 믿고 수집 (AI가 최종 판별)
                            images_found.append({"url": src, "width": w, "height": h})
                        except:
                            # 크기 확인 실패해도 URL이 정상이면 일단 추가
                            images_found.append({"url": src, "width": 0, "height": 0})
                            
                # 2. figure 안의 이미지 (보통 중요한 기사 이미지)
                figures = search_area.query_selector_all("figure img")
                for img in figures:
                    src = None
                    for attr in ["data-src", "data-original", "data-url", "src"]:
                        val = img.get_attribute(attr)
                        if val and val.startswith("http"):
                            src = val
                            break
                    
                    if src:
                         images_found.append({"url": src, "width": 0, "height": 0})

                # [DEBUG] 이미지 발견 직후 로깅
                logger.info(f"[DEBUG] {item['url']} - 원본 이미지 발견: {len(images_found)}개")
                for idx, img in enumerate(images_found[:10]):
                    logger.info(f"  [{idx+1}] {img['url'][:100]}... (w:{img['width']}, h:{img['height']})")
                
                # 중복 URL 제거
                seen_urls = set()
                candidates = []
                for img in images_found:
                    if img["url"] not in seen_urls:
                        candidates.append(img)
                        seen_urls.add(img["url"])
                
                # [DEBUG] 중복 제거 후 로깅
                logger.info(f"[DEBUG] 중복 제거 후: {len(candidates)}개")
                
                # --- AI 분석 단계 (Context check) - 병렬 처리! ---
                final_images = []
                charts = []
                
                # 기사 요약 (앞부분 500자) - AI에게 문맥 제공용
                summary = text[:500]
                
                # 최대 5개 이미지에 대해 AI 검수 (비용 조절)
                target_images = candidates[:5]
                logger.info(f"[DEBUG] AI 분석 시작: {len(target_images)}개 이미지 (병렬)")
                
                # 병렬 처리 함수
                def analyze_single_image(img):
                    analysis = _check_image_context(img["url"], item["title"], summary, referrer_url=item["url"])
                    if analysis.get("relevant"):
                        img_data = {
                            "url": img["url"],
                            "width": img.get("width", 0),
                            "height": img.get("height", 0),
                            "type": analysis.get("type", "other"),
                            "desc": analysis.get("description", "")
                        }
                        # [Local Save] 이미지 로컬 저장
                        local_path = download_image_to_local(img["url"], item["url"])
                        if local_path:
                            img_data["url"] = local_path
                        return (analysis.get("type"), img_data)
                    return None
                
                # ThreadPoolExecutor로 병렬 실행 (최대 5개 동시)
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as img_executor:
                    results = list(img_executor.map(analyze_single_image, target_images))
                
                # 결과 분류
                for result in results:
                    if result:
                        img_type, img_data = result
                        if img_type in ["chart", "table"]:
                            charts.append(img_data)
                        else:
                            final_images.append(img_data)
                
                browser.close()
                
                # [AI] 기사 분석 및 UI용 데이터 구조화 (Fact vs Opinion)
                try:
                    # 텍스트가 너무 길면 앞부분 15000자 사용 (8000 → 15000 확장, 긴 기사 후반부 킬러 포인트 확보)
                    input_text = text[:15000] 
                    
                    api_key = os.getenv("OPENAI_API_KEY")
                    if api_key and len(input_text) > 300:
                        llm_extract = ChatOpenAI(model="gpt-5-mini", api_key=api_key, temperature=1)
                        
                        analysis_prompt = f"""당신은 YouTube 크리에이터의 리서치 어시스턴트입니다.

[목적]
유튜버가 스크립트에서 "OO뉴스에 따르면..."으로 인용할 수 있는 검증 가능한 팩트를 추출합니다.
추출된 팩트가 스크립트에 녹아들어, 시청자에게 "이 영상은 근거 있는 정보를 전달한다"는 신뢰를 줍니다.

[영상 주제]
"{topic}"

⚠️ 절대 규칙:
- 기사에 없는 내용은 절대 만들지 마시오.
- 관련기사 목록의 제목은 분석 대상이 아닙니다.
- 기사 전체를 위→아래 순서로 요약하지 마시오. 선별하시오.
- 같은 내용을 다른 표현으로 반복하지 마시오.

다음 JSON 형식으로 응답하세요:

1. "source": 언론사명 (예: "매일경제", "TechCrunch")
2. "summary_short": 기사 핵심 1문장 요약 (한국어)
3. "analysis": 아래 두 리스트를 포함하는 객체:

    - "facts": 유튜버가 스크립트에 인용할 수 있는 검증 가능한 사실 (한국어)
      
      추출 기준 — 아래 4가지 유형을 각각 찾으세요:
      
      [유형A: 핵심 수치] 금액, 건수, 비율 등 임팩트 있는 숫자 (핵심 2~3개만)
        예: "앤트로픽은 API 매출 31억 달러를 보고했다"
      
      [유형B: 사건·행위] 누가 무엇을 했는지 — 스토리가 되는 것
        예: "앤트로픽은 유압식 절단기로 중고책을 분리·스캔해 AI 학습에 활용했다"
      
      [유형C: 직접 인용] 기사 속 인물/단체의 원문 발언 (큰따옴표 유지)
        예: "다리오 아모데이는 '처음 앤트로픽을 시작했을 때, 어떻게 돈을 벌지 전혀 몰랐습니다'라고 말했다"
      
      [유형D: 의외의 디테일] 시청자가 놀랄만한 에피소드, 반전, 아이러니
        예: "클로드에게 자판기를 운영시켰더니, 비싸고 쓸모없는 텅스텐 큐브를 재고로 들여놓기로 결정했다"
      
      ⚠️ 금지:
      - 같은 사실을 다른 문장으로 반복 (중복 금지)
      - "빠르게 성장하고 있다" 같은 모호한 서술
      - 영상 주제와 관련 없는 배경 정보
      - 기업이 자사 제품/서비스에 대해 주장하는 내용 → facts가 아니라 opinions의 [업계]로 분류
        예: "알리바바에 따르면 19개 벤치마크에서 경쟁력을 보였다" → [업계]
        예: "삼성은 갤럭시가 업계 최고 성능이라고 밝혔다" → [업계]

    - "opinions": 전문가/기관의 의견, 해석, 전망 (한국어)
      
      추출 규칙:
      - facts에 이미 포함된 내용을 말투만 바꿔서 넣지 마시오 (중복 금지)
      - 반드시 발언한 사람/기관의 이름이 있어야 함
      - 기사에서 찾을 수 있는 만큼만 추출 (없으면 빈 배열도 가능)
      - 억지로 개수를 채우지 마시오
      
      유형 태그: [전문가] [업계] [전망] [해석] [분석]
      - [전문가]: 이름+직함이 있는 전문가의 직접 발언
      - [업계]: 업계 관계자, 협회, 기관의 공식 입장
      - [전망]: 미래 예측 (구체적 근거가 있는 것만)
      - [해석]: 기사 속 분석가/전문가의 해석
      - [분석]: 데이터 기반 분석적 주장
      
      [좋은 예시]
      "[전문가] 다리오 아모데이(앤트로픽 CEO)는 '데이터센터를 그렇게 많이 사서 스스로를 과도하게 레버리지할 수 있을까요?'라고 경쟁사를 비꼬았다"
      "[업계] 영국출판협회는 '비난받아 마땅하다. 비밀로 유지하려 했다는 사실 자체가 문제점을 인지하고 있었음을 시사한다'고 지적했다"
      
      [나쁜 예시 - 이렇게 하지 마시오]
      "[분석] AI 기술이 발전하고 있다" ← 모호
      "[전문가] 업계에서는 성장할 것으로 보인다" ← 이름 없음
      "[전망] 매출이 100억 달러에 근접할 전망이다" ← facts에 이미 있는 내용 중복

4. "key_paragraphs": 팩트/데이터가 포함된 원본 문단 전부 (수정 없이 복사). 이중 줄바꿈으로 구분.

[기사 본문]
{input_text}
"""
                        
                        msg = HumanMessage(content=analysis_prompt)
                        res = llm_extract.invoke([msg])
                        
                        # JSON 파싱
                        content = res.content.replace("```json", "").replace("```", "").strip()
                        try:
                            data = json.loads(content)
                            gpt_source = data.get("source", "")
                            # 출처명 결정 우선순위: URL 맵 → og:site_name → GPT
                            url_source = _extract_source_from_url(item.get("url", ""))
                            og_source = item.get("og_source", "")
                            if url_source:
                                item["source"] = url_source
                            elif og_source:
                                item["source"] = og_source
                            elif gpt_source and gpt_source not in ("Unknown", "미상", "출처불명", "출처 미상", "기사(출처 미상)", "기사(제공된 본문)", ""):
                                item["source"] = gpt_source
                            else:
                                item["source"] = og_source or gpt_source or "Unknown"
                            item["summary_short"] = data.get("summary_short", "")
                            item["analysis"] = data.get("analysis", {"facts": [], "opinions": []})
                            
                            # 기존 파이프라인(Writer 등)을 위해 summary 필드에는 원문 핵심 문단을 유지
                            item["summary"] = data.get("key_paragraphs", text[:1000]) 
                            
                            logger.info(f"[AI] 기사 분석 완료: {item['source']} (Facts: {len(item['analysis'].get('facts', []))}, Opinions: {len(item['analysis'].get('opinions', []))})")
                        except json.JSONDecodeError:
                            logger.warning("[AI] JSON 파싱 실패, fallback 수행")
                            item["source"] = "Unknown"
                            item["summary_short"] = item.get("desc", "")
                            item["analysis"] = {"facts": [], "opinions": []}
                            item["summary"] = text[:1000]
                            
                    else:
                        item["source"] = "Unknown"
                        item["summary_short"] = item.get("desc", "")
                        item["analysis"] = {"facts": [], "opinions": []}
                        item["summary"] = text[:1000] + "..." 

                except Exception as e:
                    logger.warning(f"기사 분석 실패: {e}")
                    item["summary"] = text[:1000]
                    item["source"] = "Unknown"
                    item["summary_short"] = item.get("desc", "")
                    item["analysis"] = {"facts": [], "opinions": []}

                item["content"] = text
                item["images"] = final_images
                item["charts"] = charts
                return item
                
        except Exception as e:
            logger.error(f"Crawl failed {item['url']}: {e}")
            return None

    # 병렬 실행
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_one, item): item for item in articles}
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res: results.append(res)
            
    return results
