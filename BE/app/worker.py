from app.core.celery_app import celery_app
from src.script_gen.graph import generate_script
import logging
import asyncio

# 로깅 설정
logger = logging.getLogger(__name__)

import os
import base64

@celery_app.task(bind=True)
def task_generate_script(self, topic: str, channel_profile: dict, topic_request_id: str = None):
    """
    [Celery Task] 스크립트 생성 파이프라인 실행
    
    이 함수는 백그라운드 워커에 의해 실행됩니다.
    """
    try:
        logger.info(f"[Task {self.request.id}] 스크립트 생성 시작: {topic}")
        
        # generate_script는 async 함수이므로 새 이벤트 루프에서 실행
        # (Celery worker에서 기존 이벤트 루프 충돌 방지)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(generate_script(
                topic=topic,
                channel_profile=channel_profile,
                topic_request_id=topic_request_id
            ))
        finally:
            loop.close()
        
        logger.info(f"[Task {self.request.id}] 스크립트 생성 완료")
        
        # [DEBUG] 결과 데이터 확인
        logger.info(f"[DEBUG] competitor_data 존재: {result.get('competitor_data') is not None}")
        if result.get('competitor_data'):
            video_count = len(result.get('competitor_data', {}).get('video_analyses', []))
            logger.info(f"[DEBUG] competitor_data.video_analyses 개수: {video_count}")
        
        news_data = result.get("news_data", {})
        articles = news_data.get("articles", [])
        logger.info(f"[DEBUG] articles 개수: {len(articles)}")
        for i, art in enumerate(articles[:3]):  # 처음 3개만
            analysis = art.get("analysis", {})
            facts_count = len(analysis.get("facts", []))
            images_count = len(art.get("images", []))
            logger.info(f"[DEBUG] Article {i+1}: facts={facts_count}, images={images_count}")
        
        # 결과 반환 (Celery Backend인 Redis에 JSON으로 저장됨)
        # Pydantic 모델이나 복잡한 객체는 JSON 직렬화 가능한 dict로 변환되어야 함
        # generate_script는 이미 dict를 반환하므로 OK
        
        # 프론트엔드 호환성을 위한 데이터 매핑 (API 라우터 로직을 여기로 이동)
        final_script = None
        script_obj = result.get("script", {})
        
        if script_obj:
            chapters = []
            for ch in script_obj.get("chapters", []):
                # Beat 등을 합쳐서 하나의 텍스트로
                content = ch.get("narration", "")
                if not content:
                    beats = ch.get("beats", [])
                    content = "\n".join([b.get("line", "") for b in beats])
                
                chapters.append({
                    "title": ch.get("title", ""),
                    "content": content
                })
                
            final_script = {
                "hook": script_obj.get("hook", {}).get("text", ""),
                "chapters": chapters,
                "outro": script_obj.get("closing", {}).get("text", "")
            }
        
        # References 매핑 (Facts, Opinions, Images 포함)
        references = [] 
        news_data = result.get("news_data", {})
        articles = news_data.get("articles", [])
        
        for art in articles:
            if art.get("title") and art.get("url"):
                # Facts & Opinions 추출 (analysis 필드 사용)
                analysis_data = art.get("analysis", {})
                facts = analysis_data.get("facts", [])
                opinions = analysis_data.get("opinions", [])
                
                # Images + Charts 추출 및 Base64 변환
                images = []
                all_raw_images = art.get("images", []) + art.get("charts", [])
                logger.info(f"[DEBUG IMG] Article '{art.get('title', '')[:30]}...' - images: {len(art.get('images', []))}, charts: {len(art.get('charts', []))}")
                
                for img in all_raw_images:
                    if isinstance(img, dict) and img.get("url"):
                        img_url = img.get("url")
                        logger.info(f"[DEBUG IMG] Processing: {img_url}")
                        # 로컬 경로인 경우 Base64 변환 시도
                        if img_url.startswith("/"):
                            try:
                                # BE 폴더 기준 절대 경로 생성
                                be_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                                file_path = os.path.join(be_root, "public", img_url.lstrip("/"))
                                logger.info(f"[DEBUG IMG] file_path: {file_path}, exists: {os.path.exists(file_path)}")
                                if os.path.exists(file_path):
                                    with open(file_path, "rb") as f:
                                        encoded_string = base64.b64encode(f.read()).decode("utf-8")
                                        ext = img_url.split(".")[-1].lower()
                                        mime_type = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"
                                        img_url = f"data:{mime_type};base64,{encoded_string[:50]}..."  # 로그용 축약
                                        logger.info(f"[DEBUG IMG] Base64 변환 성공!")
                                        img_url = f"data:{mime_type};base64,{encoded_string}"  # 실제 데이터
                                else:
                                    logger.warning(f"Image file not found: {file_path}")
                            except Exception as e:
                                logger.warning(f"Image Base64 conversion failed: {e}")

                        images.append({
                            "url": img_url,
                            "caption": img.get("caption") or img.get("desc", ""),
                            "is_chart": img.get("is_chart", False) or (img.get("type") in ["chart", "table"])
                        })
                
                references.append({
                    "title": art.get("title"),
                    "summary": art.get("summary_short") or art.get("summary", "")[:100] + "...",
                    "source": art.get("source", "Unknown"),
                    "url": art.get("url"),
                    "date": art.get("pub_date"),
                    "analysis": {
                        "facts": facts,
                        "opinions": opinions
                    },
                    "images": images
                })
                # 디버깅용 최종 확인
                logger.info(f"[DEBUG FINAL] 기사 '{art.get('title', '')[:30]}' - facts: {len(facts)}, opinions: {len(opinions)}, images: {len(images)}")
        
        # Competitor Videos 변환
        competitor_videos = []
        competitor_data = result.get("competitor_data", {})
        if competitor_data:
            video_analyses = competitor_data.get("video_analyses", [])
            for video in video_analyses:
                competitor_videos.append({
                    "video_id": video.get("video_id"),
                    "title": video.get("title"),
                    "channel": video.get("channel"),
                    "url": video.get("url"),
                    "thumbnail": video.get("thumbnail"),
                    "hook_analysis": video.get("hook_analysis", ""),
                    "weak_points": video.get("weak_points", []),
                    "strong_points": video.get("strong_points", [])
                })
        
        return {
            "success": True,
            "message": "작업 완료",
            "script": final_script,
            "references": references,
            "competitor_videos": competitor_videos
        }
        
    except Exception as e:
        logger.error(f"[Task {self.request.id}] 실행 실패: {e}", exc_info=True)
        return {
            "success": False,
            "message": str(e),
            "script": None,
            "references": None
        }
