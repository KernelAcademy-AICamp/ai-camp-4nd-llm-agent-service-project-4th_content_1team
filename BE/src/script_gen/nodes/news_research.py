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

from app.core.config import settings

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

    # 5. 수집 결과 로깅 (팩트/의견 추출은 article_analyzer_node에서 수행)
    logger.info(f"[News Research] 기사 수집 완료: {len(full_articles)}개 기사")
    for idx, art in enumerate(full_articles, 1):
        title = (art.get("title") or "")[:60]
        source = art.get("source", "Unknown")
        content_len = len(art.get("content", ""))
        logger.info(f"  {idx}. [{source}] {title} (본문 {content_len}자)")

    return {
        "news_data": {
            "articles": full_articles,
            "structured_facts": [],    # article_analyzer_node에서 채움
            "structured_opinions": [], # article_analyzer_node에서 채움
            "queries_used": base_queries,
            "collected_at": datetime.now().isoformat()
        }
    }


def _log_research_result(
    articles: List[Dict],
    structured_facts: List[Dict],
    structured_opinions: List[str],
    queries_used: List[str],
) -> None:
    """News Research 결과를 구조화된 형식으로 로깅합니다."""
    lines = [
        "[News Research] 결과:",
        f"  검색 쿼리: {queries_used}",
        f"  기사 수: {len(articles)}개",
        f"  팩트 수: {len(structured_facts)}개",
        f"  의견 수: {len(structured_opinions)}개",
        "  기사 목록:",
    ]
    for idx, art in enumerate(articles, 1):
        title = (art.get("title") or "")[:60]
        source = art.get("source", "Unknown")
        charts = art.get("charts", [])
        facts_cnt = len(art.get("analysis", {}).get("facts", []))
        lines.append(f"    {idx}. [{source}] {title}{'...' if len(art.get('title', '') or '') > 60 else ''}")
        url = art.get("url", "")
        url_display = (url[:80] + "...") if len(url) > 80 else url
        lines.append(f"       URL: {url_display} | 팩트 {facts_cnt}개 | 차트 {len(charts)}개")
    logger.info("\n".join(lines))


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
    llm = ChatOpenAI(model="gpt-4o", api_key=api_key, temperature=0) if api_key else None

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
            
            llm = ChatOpenAI(model="gpt-4o", api_key=api_key)
            
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


def _optimize_crawl_url(url: str) -> str:
    """
    크롤링하기 어려운 URL을 접근 가능한 형태로 변환합니다.
    - 네이버 블로그: 데스크탑(iframe 구조) → 모바일(본문 직접 노출)
    - 네이버 카페: 데스크탑 → 모바일
    """
    if not url:
        return url
    # 네이버 블로그 desktop → mobile (iframe 문제 해결)
    if "blog.naver.com" in url and "m.blog.naver.com" not in url:
        return url.replace("blog.naver.com", "m.blog.naver.com")
    # 네이버 카페 desktop → mobile
    if "cafe.naver.com" in url and "m.cafe.naver.com" not in url:
        return url.replace("cafe.naver.com", "m.cafe.naver.com")
    return url


def _extract_text_fallback(html: str) -> str:
    """
    trafilatura 실패 시 BeautifulSoup으로 텍스트를 추출합니다.
    불필요한 태그 제거 후 의미 있는 줄만 반환합니다.
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer",
                         "aside", "noscript", "iframe", "form"]):
            tag.decompose()
        raw = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in raw.split("\n") if len(l.strip()) > 20]
        return "\n".join(lines)
    except Exception:
        return ""


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
                
                # 로딩 대기 (크롤링 최적화 URL 사용)
                crawl_url = _optimize_crawl_url(item["url"])
                try:
                    page.goto(crawl_url, timeout=CRAWL_TIMEOUT*1000, wait_until="domcontentloaded")

                    # [Scroll Logic] Lazy Loading 이미지 로딩을 위해 스크롤 다운
                    for _ in range(5):
                        page.evaluate("window.scrollBy(0, document.body.scrollHeight / 5)")
                        page.wait_for_timeout(2000)  # 2.0초 대기 (Wait longer for lazy loading)

                except:
                    browser.close()
                    return None

                # ── 본문 추출 (3단계 폴백) ──────────────────────────────────
                content_html = page.content()

                # 1단계: trafilatura (favor_recall=True → 더 많은 텍스트 회수)
                text = trafilatura.extract(
                    content_html,
                    include_links=False,
                    no_fallback=False,
                    favor_recall=True,
                )

                # 2단계: 네이버 블로그 iframe 내부 직접 추출
                if (not text or len(text) < 50) and "naver.com" in item["url"]:
                    try:
                        iframe = page.query_selector("iframe#mainFrame, iframe.se-main-section, #mainFrame")
                        if iframe:
                            frame = iframe.content_frame()
                            if frame:
                                frame.wait_for_load_state("domcontentloaded", timeout=10000)
                                iframe_html = frame.content()
                                text = trafilatura.extract(
                                    iframe_html,
                                    include_links=False,
                                    no_fallback=False,
                                    favor_recall=True,
                                )
                                if text and len(text) >= 50:
                                    content_html = iframe_html  # 이미지 추출도 iframe 기준으로
                                    logger.info(f"[Crawl] 네이버 iframe 본문 추출 성공: {item['url'][:60]}")
                    except Exception as iframe_err:
                        logger.debug(f"[Crawl] iframe 추출 실패: {iframe_err}")

                # 3단계: BeautifulSoup 폴백
                if not text or len(text) < 50:
                    text = _extract_text_fallback(content_html)
                    if text and len(text) >= 50:
                        logger.info(f"[Crawl] BeautifulSoup 폴백 성공: {item['url'][:60]}")

                if not text or len(text) < 50:
                    logger.warning(f"[Crawl] 본문 추출 실패 (3단계 모두 실패): {item['url'][:60]}")
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
                
                # --- AI 분석 단계 (Context check) - 비활성화 시 스킵 ──
                final_images = []
                charts = []
                
                if settings.news_image_analysis_enabled:
                    # 기사 요약 (앞부분 500자) - AI에게 문맥 제공용
                    summary = text[:500]
                    target_images = candidates[:5]
                    logger.info(f"[DEBUG] AI 이미지 분석 시작: {len(target_images)}개")

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
                            local_path = download_image_to_local(img["url"], item["url"])
                            if local_path:
                                img_data["url"] = local_path
                            return (analysis.get("type"), img_data)
                        return None

                    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as img_executor:
                        results = list(img_executor.map(analyze_single_image, target_images))
                    for result in results:
                        if result:
                            img_type, img_data = result
                            if img_type in ["chart", "table"]:
                                charts.append(img_data)
                            else:
                                final_images.append(img_data)
                else:
                    logger.info("[News Research] 이미지 AI 분석 비활성화 → 스킵")
                
                browser.close()
                
                # 출처명 추출 (URL 맵 → og:site_name 순서, GPT 없이)
                url_source = _extract_source_from_url(item.get("url", ""))
                og_source = item.get("og_source", "")
                item["source"] = url_source or og_source or "Unknown"

                # 팩트·의견 추출은 article_analyzer_node에서 수행
                item["analysis"] = {"facts": [], "opinions": []}
                item["summary_short"] = item.get("desc", "") or text[:200]
                item["summary"] = text[:3000]  # Writer가 참고할 원문 유지

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
