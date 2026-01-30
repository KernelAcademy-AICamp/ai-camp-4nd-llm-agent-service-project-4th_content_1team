import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.competitor import CompetitorCollection, CompetitorVideo, VideoCommentSample
from app.schemas.competitor import CompetitorSaveRequest

logger = logging.getLogger(__name__)


class CompetitorService:

    @staticmethod
    async def save_collection(
        db: AsyncSession, req: CompetitorSaveRequest
    ) -> CompetitorCollection:
        collection = CompetitorCollection(policy_json=req.policy_json)

        for v in req.videos:
            collection.videos.append(
                CompetitorVideo(
                    youtube_video_id=v.youtube_video_id,
                    url=v.url,
                    title=v.title,
                    channel_title=v.channel_title,
                    published_at=v.published_at,
                    duration_sec=v.duration_sec,
                    metrics_json=v.metrics_json,
                    caption_meta_json=v.caption_meta_json,
                    selection_json=v.selection_json,
                )
            )

        db.add(collection)
        await db.commit()
        await db.refresh(collection, ["videos"])
        
        # 모든 영상의 댓글 자동 가져오기 (각 영상당 50개씩)
        if collection.videos:
            success_count = 0
            failed_count = 0
            
            for video in collection.videos:
                try:
                    await CompetitorService.fetch_and_save_comments(
                        db,
                        video.id,
                        max_results=50,
                    )
                    success_count += 1
                    logger.info(
                        f"영상 댓글 자동 저장 완료 ({success_count}/{len(collection.videos)}): {video.youtube_video_id}"
                    )
                except Exception as e:
                    failed_count += 1
                    # 댓글 가져오기 실패해도 영상 저장은 성공한 것으로 처리
                    logger.warning(
                        f"영상 댓글 자동 저장 실패 ({failed_count}/{len(collection.videos)}): {video.youtube_video_id} - {e}",
                        exc_info=True
                    )
            
            logger.info(
                f"댓글 가져오기 완료: 성공 {success_count}개, 실패 {failed_count}개 / 총 {len(collection.videos)}개"
            )
        
        return collection

    @staticmethod
    async def fetch_and_save_comments(
        db: AsyncSession,
        competitor_video_id: UUID,
        max_results: int = 10,
    ) -> List[VideoCommentSample]:
        """
        가장 최상위 영상의 댓글을 좋아요, 싫어요, 하트 순으로 가져와서 DB에 저장.
        
        Args:
            db: 데이터베이스 세션
            competitor_video_id: 경쟁 영상 ID
            max_results: 가져올 댓글 수 (기본 10개)
            
        Returns:
            저장된 댓글 샘플 리스트
        """
        # 1. 경쟁 영상 조회
        result = await db.execute(
            select(CompetitorVideo).where(CompetitorVideo.id == competitor_video_id)
        )
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(
                status_code=404,
                detail=f"경쟁 영상을 찾을 수 없습니다: {competitor_video_id}"
            )
        
        # 2. YouTube 댓글 API로 댓글 가져오기
        # 정렬 후 필터링을 위해 더 많이 가져옴 (YouTube API 최대 100개)
        fetch_count = min(max_results * 2, 100)
        comments_data = await CompetitorService._fetch_youtube_comments(
            video.youtube_video_id,
            max_results=fetch_count,
        )
        
        if not comments_data:
            logger.warning(f"댓글을 찾을 수 없습니다: {video.youtube_video_id}")
            return []
        
        # 3. 좋아요, 싫어요, 하트 순으로 정렬
        sorted_comments = CompetitorService._sort_comments_by_engagement(comments_data)
        
        # 4. 상위 N개만 선택
        top_comments = sorted_comments[:max_results]
        
        # 5. 기존 댓글 삭제 (중복 방지)
        await db.execute(
            delete(VideoCommentSample).where(
                VideoCommentSample.competitor_video_id == competitor_video_id
            )
        )
        await db.flush()
        
        # 6. 새 댓글 저장
        comment_samples = []
        for comment_data in top_comments:
            comment_sample = VideoCommentSample(
                competitor_video_id=competitor_video_id,
                comment_id=comment_data.get("comment_id"),
                text=comment_data.get("text", ""),
                likes=comment_data.get("likes"),
                published_at=comment_data.get("published_at"),
            )
            db.add(comment_sample)
            comment_samples.append(comment_sample)
        
        await db.commit()
        
        # 7. 저장된 댓글 새로고침
        for comment in comment_samples:
            await db.refresh(comment)
        
        logger.info(
            f"댓글 {len(comment_samples)}개 저장 완료: {competitor_video_id}"
        )
        
        return comment_samples

    @staticmethod
    async def _fetch_youtube_comments(
        video_id: str,
        max_results: int = 100,
    ) -> List[dict]:
        """
        YouTube Data API v3의 commentThreads.list를 사용하여 댓글 가져오기.
        
        Args:
            video_id: YouTube 비디오 ID
            max_results: 가져올 최대 댓글 수
            
        Returns:
            댓글 데이터 리스트
        """
        BASE_URL = "https://www.googleapis.com/youtube/v3"
        api_key = settings.youtube_api_key
        
        all_comments = []
        next_page_token = None
        
        try:
            while len(all_comments) < max_results:
                # 한 번에 가져올 수 있는 최대 댓글 수는 100개
                fetch_count = min(100, max_results - len(all_comments))
                
                params = {
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": fetch_count,
                    "order": "relevance",  # 관련성 순으로 가져온 후 좋아요 순으로 재정렬
                    "key": api_key,
                }
                
                if next_page_token:
                    params["pageToken"] = next_page_token
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        f"{BASE_URL}/commentThreads",
                        params=params,
                    )
                    
                    # 할당량 초과 처리
                    if resp.status_code == 403:
                        error_data = resp.json()
                        error_reason = (
                            error_data.get("error", {})
                            .get("errors", [{}])[0]
                            .get("reason", "")
                        )
                        if "quotaExceeded" in error_reason:
                            raise HTTPException(
                                status_code=429,
                                detail="YouTube API 일일 할당량 초과",
                            )
                    
                    resp.raise_for_status()
                    data = resp.json()
                    
                    # 댓글 파싱
                    items = data.get("items", [])
                    for item in items:
                        comment = CompetitorService._parse_comment_item(item)
                        if comment:
                            all_comments.append(comment)
                    
                    # 다음 페이지 토큰 확인
                    next_page_token = data.get("nextPageToken")
                    if not next_page_token:
                        break
                    
                    # 댓글이 없으면 종료
                    if not items:
                        break
        
        except httpx.TimeoutException:
            logger.error(f"YouTube 댓글 API timeout: {video_id}")
            raise HTTPException(
                status_code=504,
                detail="YouTube API 요청 시간 초과",
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"YouTube 댓글 API error: {e}")
            if e.response.status_code == 404:
                # 댓글이 비활성화된 경우
                logger.info(f"댓글이 비활성화되었거나 없습니다: {video_id}")
                return []
            raise HTTPException(
                status_code=500,
                detail=f"댓글 조회 중 오류 발생: {str(e)}",
            )
        
        return all_comments

    @staticmethod
    def _parse_comment_item(item: dict) -> Optional[dict]:
        """
        YouTube API 응답의 댓글 아이템을 파싱.
        
        Args:
            item: commentThreads API 응답의 item
            
        Returns:
            파싱된 댓글 데이터 또는 None
        """
        try:
            snippet = item.get("snippet", {})
            top_level_comment = snippet.get("topLevelComment", {})
            comment_snippet = top_level_comment.get("snippet", {})
            
            # 댓글 ID
            comment_id = top_level_comment.get("id")
            
            # 댓글 텍스트
            text = comment_snippet.get("textDisplay", "")
            
            # 좋아요 수
            like_count = comment_snippet.get("likeCount", 0)
            
            # 싫어요 수 (YouTube API v3에서는 더 이상 제공하지 않음)
            # 하지만 다른 반응(하트 등)도 likeCount에 포함될 수 있음
            dislike_count = 0  # API에서 제공하지 않음
            
            # 게시 시간
            published_at_str = comment_snippet.get("publishedAt")
            published_at = None
            if published_at_str:
                try:
                    published_at = datetime.fromisoformat(
                        published_at_str.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid publishedAt format: {published_at_str}")
            
            return {
                "comment_id": comment_id,
                "text": text,
                "likes": like_count,
                "dislikes": dislike_count,
                "published_at": published_at,
            }
        except Exception as e:
            logger.warning(f"댓글 파싱 실패: {e}")
            return None

    @staticmethod
    def _sort_comments_by_engagement(comments: List[dict]) -> List[dict]:
        """
        댓글을 좋아요, 싫어요, 하트 순으로 정렬.
        
        참고: YouTube API v3에서는 싫어요 수를 제공하지 않으므로,
        좋아요 수를 기준으로 정렬합니다.
        
        Args:
            comments: 댓글 데이터 리스트
            
        Returns:
            정렬된 댓글 리스트 (좋아요 수 내림차순)
        """
        # 좋아요 수를 기준으로 내림차순 정렬
        # 좋아요 수가 같으면 최신순으로 정렬
        return sorted(
            comments,
            key=lambda x: (
                -(x.get("likes", 0) or 0),  # 좋아요 수 내림차순
                x.get("published_at") or datetime.min,  # 최신순
            ),
        )
