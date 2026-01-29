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
import difflib  # 유사도 비교용
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
    logger.info("News Research Node (Advanced) 시작")
    
    # 1. 입력 데이터
    content_brief = state.get("content_brief", {})
    research_plan = content_brief.get("researchPlan", {})
    base_queries = research_plan.get("newsQuery", [])
    
    if not base_queries:
        return {"news_data": {"articles": []}}
    
    # 2. 뉴스 대량 수집 (Deep Fetch)
    # 쿼리당 15개씩 수집 -> 후보군 확보
    logger.info(f"뉴스 후보군 수집 시작: 쿼리당 15개")
    raw_articles = _fetch_naver_news_bulk(base_queries)
    logger.info(f"뉴스 후보군 확보: {len(raw_articles)}개")
    
    # 3. 중복 제거 및 대표 기사 선정 (Smart Dedup)
    # 비슷한 기사는 묶어서 버리고, 서로 다른 주제의 알짜 기사만 남김
    unique_articles = _deduplicate_articles(raw_articles)
    logger.info(f"중복 제거 후 선별된 Top 기사: {len(unique_articles)}개")
    
    # 4. 본문 및 이미지 정밀 크롤링 (Crawling & AI Analysis)
    # 선별된 Top 기사들에 대해서만 정밀 분석 수행 (비용 절감)
    full_articles = _crawl_and_analyze(unique_articles)
    
    # 5. 결과 반환 (차트가 있는 기사 우선 정렬)
    full_articles.sort(key=lambda x: (len(x.get("charts", [])), len(x.get("images", []))), reverse=True)
    
    return {
        "news_data": {
            "articles": full_articles,
            "queries_used": base_queries,
            "collected_at": datetime.now().isoformat()
        }
    }


def _fetch_naver_news_bulk(queries: List[str]) -> List[Dict]:
    """네이버 뉴스 검색결과를 대량으로 가져옵니다 (쿼리당 15개)."""
    articles = []
    seen_links = set()
    
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logger.error("NAVER API Key Missing")
        return []

    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    url = "https://openapi.naver.com/v1/search/news.json"
    
    for query in queries:
        try:
            # 15개 수집 (display=15)
            params = {"query": query, "display": 15, "sort": "sim"}
            res = requests.get(url, headers=headers, params=params, timeout=5)
            
            if res.status_code == 200:
                items = res.json().get("items", [])
                for item in items:
                    link = item.get("originallink") or item.get("link")
                    if link and link not in seen_links:
                        clean_title = re.sub('<[^<]+?>', '', item.get("title", ""))
                        clean_desc = re.sub('<[^<]+?>', '', item.get("description", ""))
                        
                        articles.append({
                            "title": clean_title,
                            "url": link,
                            "desc": clean_desc,
                            "pub_date": item.get("pubDate"),
                            "query": query
                        })
                        seen_links.add(link)
        except Exception as e:
            logger.warning(f"Naver Search Error ({query}): {e}")
            
    return articles


def _deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """
    유사한 제목을 가진 기사들을 그룹화하고, 
    각 그룹에서 가장 영양가 있는(설명이 길거나 키워드가 있는) 기사를 하나씩 뽑아냅니다.
    최종적으로 Top 3~5개만 리턴합니다.
    """
    if not articles:
        return []
        
    clusters = []
    visited = [False] * len(articles)
    
    # 1. Clustering (유사도 기반 그룹핑)
    for i in range(len(articles)):
        if visited[i]:
            continue
            
        current_cluster = [articles[i]]
        visited[i] = True
        
        for j in range(i + 1, len(articles)):
            if visited[j]:
                continue
                
            # 문장 유사도 비교 (제목 OR 내용 OR 키워드) - 셋 중 하나라도 높으면 중복으로 간주
            title_sim = difflib.SequenceMatcher(None, articles[i]["title"], articles[j]["title"]).ratio()
            desc_sim = difflib.SequenceMatcher(None, articles[i]["desc"], articles[j]["desc"]).ratio()
            
            # 키워드 기반 유사도 (Jaccard Similarity)
            # 제목을 단어로 분리하여 교집합 비율 계산
            words_i = set(articles[i]["title"].split())
            words_j = set(articles[j]["title"].split())
            intersection = len(words_i & words_j)
            union = len(words_i | words_j)
            keyword_sim = intersection / union if union > 0 else 0
            
            # 제목 40% 이상 OR 내용 70% 이상 OR 키워드 50% 이상 비슷하면 같은 기사
            if title_sim >= 0.4 or desc_sim >= 0.7 or keyword_sim >= 0.5:
                current_cluster.append(articles[j])
                visited[j] = True
        
        clusters.append(current_cluster)
    
    # 2. Representative Selection (대표 기사 선정)
    final_articles = []
    for cluster in clusters:
        # 점수 계산: 설명 길이 + ('표'/'그래프' 키워드 가산점)
        best_article = cluster[0]
        max_score = -1
        
        for art in cluster:
            score = len(art["desc"])  # 기본 점수: 설명이 자세할수록 좋음
            
            # 가산점: 표/그래프/종합/분석 같은 단어가 있으면 데이터가 많을 확률 높음
            keywords = ["표", "그래프", "차트", "추이", "현황", "종합", "분석"]
            if any(k in art["title"] for k in keywords):
                score += 200
            if any(k in art["desc"] for k in keywords):
                score += 100
            
            if score > max_score:
                max_score = score
                best_article = art
                
        final_articles.append(best_article)
        
    # 최대 5개까지만 반환 (다양성 확보된 상태)
    return final_articles[:5]



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
        save_dir = "public/images/news"
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


def _crawl_and_analyze(articles: List[Dict]) -> List[Dict]:
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
                
                # --- AI 분석 단계 (Context check) ---
                final_images = []
                charts = []
                
                # 기사 요약 (앞부분 500자) - AI에게 문맥 제공용
                summary = text[:500]
                
                # 최대 5개 이미지에 대해 AI 검수 (비용 조절) [Change] 8 -> 5
                logger.info(f"[DEBUG] AI 분석 시작: {len(candidates[:5])}개 이미지")
                for img in candidates[:5]:
                    # Referer로 기사 URL 전달하여 Hotlink Protection 우회
                    analysis = _check_image_context(img["url"], item["title"], summary, referrer_url=item["url"])
                    
                    # [DEBUG] AI 분석 결과 로깅
                    if not analysis.get("relevant"):
                        logger.debug(f"[AI] 거부됨: {img['url'][:80]} - {analysis}")
                    
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
                        else:
                            # 저장 실패하면 원본 유지 (혹은 제외 정책에 따라 continue 가능)
                            pass
                        
                        # [분리 로직] 차트/표는 charts에만, 나머지는 images에만 넣기
                        if analysis.get("type") in ["chart", "table"]:
                            charts.append(img_data)
                        else:
                            final_images.append(img_data)
                
                browser.close()
                
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
