import json
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.competitor import CompetitorCollection, CompetitorVideo, VideoCommentSample
from app.models.caption import VideoCaption
from app.models.video_content_analysis import VideoContentAnalysis
from app.schemas.competitor import CompetitorSaveRequest
from app.services.subtitle_service import SubtitleService

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
        
        # 2. 비디오의 채널 ID 가져오기 (채널 주인 댓글 필터링용)
        video_channel_id = await CompetitorService._get_video_channel_id(
            video.youtube_video_id
        )
        
        # 3. YouTube 댓글 API로 댓글 가져오기
        # 정렬 후 필터링을 위해 더 많이 가져옴 (YouTube API 최대 100개)
        fetch_count = min(max_results * 2, 100)
        comments_data = await CompetitorService._fetch_youtube_comments(
            video.youtube_video_id,
            max_results=fetch_count,
        )
        
        if not comments_data:
            logger.warning(f"댓글을 찾을 수 없습니다: {video.youtube_video_id}")
            return []
        
        # 4. 채널 주인 댓글 제외
        if video_channel_id:
            filtered_comments = [
                comment
                for comment in comments_data
                if comment.get("author_channel_id") != video_channel_id
            ]
            
            excluded_count = len(comments_data) - len(filtered_comments)
            if excluded_count > 0:
                logger.info(
                    f"채널 주인 댓글 {excluded_count}개 제외: 전체 {len(comments_data)}개 중 {len(filtered_comments)}개 남음"
                )
        else:
            # 채널 ID를 가져올 수 없는 경우 필터링 건너뛰기
            filtered_comments = comments_data
            logger.warning(
                f"비디오 채널 ID를 가져올 수 없어 채널 주인 댓글 필터링을 건너뜁니다: {video.youtube_video_id}"
            )
        
        if not filtered_comments:
            logger.warning(
                f"채널 주인 댓글 제외 후 댓글이 없습니다: {video.youtube_video_id}"
            )
            return []
        
        # 5. 좋아요, 싫어요, 하트 순으로 정렬
        sorted_comments = CompetitorService._sort_comments_by_engagement(filtered_comments)
        
        # 6. 상위 N개만 선택
        top_comments = sorted_comments[:max_results]
        
        # 7. 기존 댓글 삭제 (중복 방지)
        await db.execute(
            delete(VideoCommentSample).where(
                VideoCommentSample.competitor_video_id == competitor_video_id
            )
        )
        await db.flush()
        
        # 8. 새 댓글 저장
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
        
        # 9. 저장된 댓글 새로고침
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
            
            # 댓글 작성자의 채널 ID
            author_channel_id = None
            author_channel = comment_snippet.get("authorChannelId")
            if author_channel and isinstance(author_channel, dict):
                author_channel_id = author_channel.get("value")
            
            return {
                "comment_id": comment_id,
                "text": text,
                "likes": like_count,
                "dislikes": dislike_count,
                "published_at": published_at,
                "author_channel_id": author_channel_id,
            }
        except Exception as e:
            logger.warning(f"댓글 파싱 실패: {e}")
            return None

    @staticmethod
    async def _get_video_channel_id(video_id: str) -> Optional[str]:
        """
        YouTube 비디오의 채널 ID를 가져오기.
        
        Args:
            video_id: YouTube 비디오 ID
            
        Returns:
            채널 ID 또는 None
        """
        BASE_URL = "https://www.googleapis.com/youtube/v3"
        api_key = settings.youtube_api_key
        
        params = {
            "part": "snippet",
            "id": video_id,
            "key": api_key,
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{BASE_URL}/videos",
                    params=params,
                )
                
                if resp.status_code == 403:
                    error_data = resp.json()
                    error_reason = (
                        error_data.get("error", {})
                        .get("errors", [{}])[0]
                        .get("reason", "")
                    )
                    if "quotaExceeded" in error_reason:
                        logger.warning("YouTube API 할당량 초과로 채널 ID 조회 실패")
                        return None
                
                resp.raise_for_status()
                data = resp.json()
                
                items = data.get("items", [])
                if items:
                    snippet = items[0].get("snippet", {})
                    return snippet.get("channelId")
                
                return None
        except Exception as e:
            logger.warning(f"비디오 채널 ID 조회 실패: {video_id} - {e}")
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

    # ── 영상 자막 기반 LLM 분석 ─────────────────────────────

    @staticmethod
    def _extract_text_from_segments(seg: dict) -> Optional[str]:
        """segments_json에서 자막 텍스트 추출."""
        if seg.get("no_captions"):
            return None
        tracks = seg.get("tracks", [])
        texts = []
        for track in tracks:
            for cue in track.get("cues", []):
                t = (cue.get("text") or "").strip() if isinstance(cue.get("text"), str) else ""
                if t:
                    texts.append(t)
        return " ".join(texts) if texts else None

    @staticmethod
    async def get_or_fetch_caption_text(
        db: AsyncSession,
        competitor_video: CompetitorVideo,
    ) -> Optional[str]:
        """
        CompetitorVideo의 자막 텍스트를 반환.
        동일 youtube_video_id의 어떤 CompetitorVideo에 연결된 자막이든 사용.
        DB에 없으면 SubtitleService로 조회 후 저장.
        """
        # 1. VideoCaption 조회 - youtube_video_id로 검색 (어떤 CompetitorVideo든 상관없음)
        result = await db.execute(
            select(VideoCaption)
            .join(CompetitorVideo, VideoCaption.competitor_video_id == CompetitorVideo.id)
            .where(CompetitorVideo.youtube_video_id == competitor_video.youtube_video_id)
            .limit(1)
        )
        caption = result.scalar_one_or_none()

        if caption and caption.segments_json:
            text = CompetitorService._extract_text_from_segments(caption.segments_json)
            if text:
                return text

        # 2. 자막 없으면 fetch (한국어 우선, 없으면 영어, 첫 성공 시 즉시 종료)
        results = await SubtitleService.fetch_subtitles(
            video_ids=[competitor_video.youtube_video_id],
            languages=["ko", "en"],  # 최소화: 429 방지
            db=db,
        )
        if not results:
            return None
        r = results[0]
        if r.get("no_captions") or r.get("status") in ("no_subtitle", "failed"):
            logger.info(
                f"자막 조회 실패 [{competitor_video.youtube_video_id}]: "
                f"status={r.get('status')}, no_captions={r.get('no_captions')}, error={r.get('error')}"
            )
            return None
        tracks = r.get("tracks", [])
        texts = []
        for track in tracks:
            for cue in track.get("cues", []):
                t = cue.get("text", "").strip() if isinstance(cue.get("text"), str) else ""
                if t:
                    texts.append(t)
        return " ".join(texts) if texts else None

    @staticmethod
    async def analyze_video_content(
        db: AsyncSession,
        youtube_video_id: str,
    ) -> VideoContentAnalysis:
        """
        youtube_video_id로 경쟁 영상을 찾아 자막 기반 LLM 분석 수행.
        캐시가 있으면 반환, 없으면 분석 후 저장.
        """
        # 1. CompetitorVideo 조회 (동일 영상이 여러 컬렉션에 있을 수 있으므로 first 사용)
        result = await db.execute(
            select(CompetitorVideo)
            .where(CompetitorVideo.youtube_video_id == youtube_video_id)
            .order_by(CompetitorVideo.id.desc())
            .limit(1)
        )
        video = result.scalar_one_or_none()
        if not video:
            raise HTTPException(
                status_code=404,
                detail="저장된 경쟁 영상을 찾을 수 없습니다. 먼저 경쟁 영상 검색을 수행해 주세요.",
            )

        # 2. 캐시 조회
        result = await db.execute(
            select(VideoContentAnalysis).where(
                VideoContentAnalysis.competitor_video_id == video.id
            )
        )
        cached = result.scalar_one_or_none()
        if cached:
            return cached

        # 3. 자막 텍스트 획득
        caption_text = await CompetitorService.get_or_fetch_caption_text(db, video)
        if not caption_text or len(caption_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="이 영상은 자막을 사용할 수 없어 분석할 수 없습니다.",
            )

        # 4. LLM 분석
        api_key = settings.openai_api_key
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="OpenAI API 키가 설정되지 않았습니다.",
            )

        # 자막이 너무 길면 앞부분만 사용 (토큰 제한)
        max_chars = 12000
        if len(caption_text) > max_chars:
            caption_text = caption_text[:max_chars] + "..."

        llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
        prompt = f"""You are a professional YouTube content analyst and strategist. Your job is to evaluate video content quality, information value, logical structure, delivery effectiveness, and viewer impact based strictly on the caption transcript.

Perform a critical, expert-level analysis — not a surface summary.
Evaluation dimensions you MUST consider:
- Core message and argument structure
- Information density and practical value
- Logical flow and explanation clarity
- Persuasiveness and credibility
- Viewer comprehension and usefulness
- Redundancy, vagueness, exaggeration, unsupported claims
- Delivery effectiveness and content structure quality
- Strengths and weaknesses from a creator improvement perspective

Rules:
- Do NOT produce shallow summaries
- Do NOT use generic praise or vague statements
- Every strength and weakness must be concrete and actionable
- Base judgments on transcript evidence, not assumptions
- Be analytical and critical, not promotional
- Write the analysis content in Korean
- Output must be valid JSON only — no extra text

Style requirements for your writing:
- Write the final content in Korean
- Use easy, conversational spoken-style Korean that general audiences can understand
- Avoid technical jargon unless absolutely necessary
- If you use technical terms, briefly explain them in simple words
- Do not sound academic or formal — sound like a smart but friendly reviewer
- Be specific and concrete, not generic

Strict rules:
- No shallow summaries
- No generic praise
- No marketing tone
- Every strength must be concrete
- Every weakness MUST include a specific reason or evidence from the transcript
- Weakness lines must include cause or proof using phrases like:
  “왜냐하면”, “예를 들어”, “자막에서 보면”, “~라고 말하지만”, “구체적으로는”
- Do not invent facts outside the transcript
- Base judgments only on transcript evidence
- Output must be valid JSON only — no extra text

Video title: {video.title}

[Caption Transcript]
{caption_text}

Respond ONLY in the following JSON format (no extra text):
{{
  "summary": "영상의 핵심 내용을 3~5문장으로 요약",
  "strengths": ["장점1", "장점2", "장점3"],
  "weaknesses": ["부족한점1", "부족한점2, 부족한점3"]
}}"""

        try:
            res = llm.invoke([HumanMessage(content=prompt)])
            content = res.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"LLM 분석 파싱 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail="영상 분석 중 오류가 발생했습니다.",
            )

        summary = parsed.get("summary", "")
        strengths = parsed.get("strengths", [])
        weaknesses = parsed.get("weaknesses", [])
        if not isinstance(strengths, list):
            strengths = [str(s) for s in strengths] if strengths else []
        if not isinstance(weaknesses, list):
            weaknesses = [str(w) for w in weaknesses] if weaknesses else []

        # 5. DB 저장
        analysis = VideoContentAnalysis(
            competitor_video_id=video.id,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        return analysis
