from app.core.celery_app import celery_app
from src.script_gen.graph import generate_script
import logging
import asyncio

# 로깅 설정
logger = logging.getLogger(__name__)

import os
import base64
import uuid


async def _save_result_to_db(topic_request_id: str, formatted: dict):
    """파이프라인 결과를 DB에 저장"""
    from app.core.db import AsyncSessionLocal
    from app.models.topic_request import TopicRequest
    from app.models.script_output import ScriptDraft, VerifiedScript

    async with AsyncSessionLocal() as session:
        try:
            # 1. TopicRequest 상태 업데이트
            from sqlalchemy import select
            stmt = select(TopicRequest).where(TopicRequest.id == topic_request_id)
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row:
                row.status = "verified" if formatted.get("script") else "failed"
            
            # 2. ScriptDraft 저장
            if formatted.get("script"):
                draft = ScriptDraft(
                    id=uuid.uuid4(),
                    topic_request_id=topic_request_id,
                    script_json=formatted["script"],
                    metadata_json={
                        "references_count": len(formatted.get("references", [])),
                        "competitor_count": len(formatted.get("competitor_videos", [])),
                    },
                )
                session.add(draft)

            # 3. VerifiedScript 저장 (전체 포맷된 결과)
            verified = VerifiedScript(
                id=uuid.uuid4(),
                topic_request_id=topic_request_id,
                final_script_json=formatted.get("script"),
                source_map_json={
                    "references": formatted.get("references", []),
                    "competitor_videos": formatted.get("competitor_videos", []),
                    "citations": formatted.get("citations", []),
                },
            )
            session.add(verified)

            await session.commit()
            logger.info(f"[DB] 결과 저장 완료 (topic_request_id={topic_request_id})")
        except Exception as e:
            await session.rollback()
            logger.error(f"[DB] 결과 저장 실패: {e}", exc_info=True)


async def _create_topic_request(topic: str, user_id: str = None, channel_id: str = None, topic_keywords: list = None):
    """TopicRequest 레코드 생성"""
    from app.core.db import AsyncSessionLocal
    from app.models.topic_request import TopicRequest

    if not user_id:
        raise ValueError("user_id is required to create a TopicRequest")

    request_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        try:
            tr = TopicRequest(
                id=request_id,
                user_id=user_id,
                channel_id=channel_id,
                topic_title=topic,
                topic_keywords=topic_keywords or [],  # channel_topics/trend_topics의 search_keywords
                status="created",
            )
            session.add(tr)
            await session.commit()
            logger.info(f"[DB] TopicRequest 생성: {request_id}")
        except Exception as e:
            await session.rollback()
            logger.error(f"[DB] TopicRequest 생성 실패: {e}", exc_info=True)
            raise  # 실패 시 호출자에게 전파
    return str(request_id)


@celery_app.task(bind=True)
def task_generate_script(self, topic: str, channel_profile: dict, topic_request_id: str = None, user_id: str = None, channel_id: str = None):
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
            # TopicRequest가 없으면 생성
            if not topic_request_id:
                # channel_profile 안의 topic_context에서 search_keywords를 꺼냄
                topic_context = channel_profile.get("topic_context", {})
                search_keywords = topic_context.get("search_keywords", []) if topic_context else []
                topic_request_id = loop.run_until_complete(
                    _create_topic_request(topic, user_id, channel_id, topic_keywords=search_keywords)
                )
            
            result = loop.run_until_complete(generate_script(
                topic=topic,
                channel_profile=channel_profile,
                topic_request_id=topic_request_id
            ))
        
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
            
            # 프론트엔드 호환성을 위한 데이터 매핑
            final_script = None
            script_obj = result.get("script", {})
            
            if script_obj:
                chapters = []
                for ch in script_obj.get("chapters", []):
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
                            if img_url.startswith("/"):
                                try:
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
            
            # Citations 배열 생성 (기사 기준 ①②③ → 출처 매핑)
            CIRCLE_NUMBERS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
                              "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳"]
            
            structured_facts = news_data.get("structured_facts", [])
            
            # 스크립트 전체 텍스트 조합 (실제 사용된 마커 필터링용)
            script_full_text = ""
            if final_script:
                script_full_text = (final_script.get("hook", "") + " "
                    + " ".join(ch.get("content", "") for ch in final_script.get("chapters", []))
                    + " " + final_script.get("outro", ""))
            
            all_citations = []
            article_idx_to_marker = {}  # 기사 인덱스 → 마커 매핑
            next_marker_idx = 0
            
            for fact in structured_facts:
                # 확정된 source_index를 우선 사용 (news_research에서 하드코딩)
                source_article = None
                art_idx = fact.get("source_index")
                
                if art_idx is not None and 0 <= art_idx < len(articles):
                    source_article = articles[art_idx]
                else:
                    # 호환: 기존 source_indices fallback
                    source_indices = fact.get("source_indices", [])
                    if source_indices and isinstance(source_indices, list):
                        first_idx = source_indices[0] if isinstance(source_indices[0], int) else None
                        if first_idx is not None and 0 <= first_idx < len(articles):
                            source_article = articles[first_idx]
                            art_idx = first_idx
                
                # 기사 인덱스 기준으로 마커 할당 (같은 기사 = 같은 번호)
                if art_idx is not None:
                    if art_idx not in article_idx_to_marker:
                        marker = CIRCLE_NUMBERS[next_marker_idx] if next_marker_idx < len(CIRCLE_NUMBERS) else f"[{next_marker_idx+1}]"
                        article_idx_to_marker[art_idx] = {
                            "marker": marker,
                            "number": next_marker_idx + 1,
                        }
                        next_marker_idx += 1
                    info = article_idx_to_marker[art_idx]
                else:
                    # 출처 기사를 못 찾으면 새 번호 할당
                    marker = CIRCLE_NUMBERS[next_marker_idx] if next_marker_idx < len(CIRCLE_NUMBERS) else f"[{next_marker_idx+1}]"
                    info = {"marker": marker, "number": next_marker_idx + 1}
                    next_marker_idx += 1
                
                # source_name(확정)을 우선 사용, 없으면 article에서 가져옴
                source_display = fact.get("source_name") or (source_article.get("source", "Unknown") if source_article else "Unknown")
                
                all_citations.append({
                    "marker": info["marker"],
                    "number": info["number"],
                    "fact_id": fact.get("id"),
                    "content": fact.get("content"),
                    "category": fact.get("category", "Fact"),
                    "source": source_display,
                    "source_title": source_article.get("title", "") if source_article else "",
                    "source_url": fact.get("article_url") or (source_article.get("url", "") if source_article else ""),
                })
            
            # 스크립트에 실제 사용된 마커만 필터링
            # all_citations의 모든 마커를 검사 (①~⑳ 뿐 아니라 [21] 등 대괄호 형식도 포함)
            used_markers = set()
            for c in all_citations:
                if c["marker"] in script_full_text:
                    used_markers.add(c["marker"])
            
            if used_markers:
                citations = [c for c in all_citations if c["marker"] in used_markers]
            else:
                citations = all_citations  # 마커 찾기 실패 시 전체 표시 (안전 fallback)
            
            formatted_result = {
                "success": True,
                "message": "작업 완료",
                "script": final_script,
                "references": references,
                "competitor_videos": competitor_videos,
                "citations": citations
            }
            
            # ====== DB에 결과 저장 ======
            if topic_request_id:
                try:
                    loop.run_until_complete(
                        _save_result_to_db(
                            topic_request_id=topic_request_id,
                            formatted=formatted_result,
                        )
                    )
                except Exception as e:
                    logger.error(f"[DB 저장 실패] {e}", exc_info=True)
        finally:
            loop.close()  # 성공/실패 무관하게 반드시 루프 닫기
        
        # topic_request_id를 결과에 포함 (프론트에서 조회용)
        formatted_result["topic_request_id"] = topic_request_id
        return formatted_result
        
    except Exception as e:
        logger.error(f"[Task {self.request.id}] 실행 실패: {e}", exc_info=True)
        return {
            "success": False,
            "message": str(e),
            "script": None,
            "references": None
        }


@celery_app.task(bind=True)
def task_update_all_competitor_videos(self):
    """
    [Celery Task] 모든 경쟁 유튜버의 최신 영상 업데이트

    매일 스케줄로 실행되어 등록된 모든 경쟁 채널의 최신 영상 3개를 가져옴
    """
    try:
        logger.info(f"[Task {self.request.id}] 경쟁 유튜버 최신 영상 업데이트 시작")

        # 비동기 함수 실행
        result = asyncio.get_event_loop().run_until_complete(
            _update_all_competitor_videos_async()
        )

        logger.info(f"[Task {self.request.id}] 경쟁 유튜버 최신 영상 업데이트 완료: {result}")
        return result

    except Exception as e:
        logger.error(f"[Task {self.request.id}] 실행 실패: {e}", exc_info=True)
        return {
            "success": False,
            "message": str(e),
            "updated_count": 0
        }


async def _update_all_competitor_videos_async():
    """경쟁 유튜버 최신 영상 업데이트 (비동기)"""
    from sqlalchemy import select

    from app.core.db import AsyncSessionLocal
    from app.models.competitor_channel import CompetitorChannel
    from app.services.competitor_channel_service import CompetitorChannelService

    updated_count = 0
    failed_count = 0

    async with AsyncSessionLocal() as db:
        # 모든 경쟁 채널 조회
        result = await db.execute(select(CompetitorChannel))
        channels = result.scalars().all()

        logger.info(f"총 {len(channels)}개 경쟁 채널 업데이트 시작")

        for channel in channels:
            try:
                # 서비스 메서드 사용 (영상 + 댓글 저장)
                await CompetitorChannelService._save_recent_videos(
                    db, channel.id, channel.channel_id
                )
                await db.commit()
                updated_count += 1
                logger.info(f"채널 '{channel.title}' 업데이트 완료")

            except Exception as e:
                failed_count += 1
                logger.error(f"채널 '{channel.title}' 업데이트 실패: {e}")
                await db.rollback()

    return {
        "success": True,
        "message": f"{updated_count}개 채널 업데이트 완료, {failed_count}개 실패",
        "updated_count": updated_count,
        "failed_count": failed_count
    }
