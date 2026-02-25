import logging
import time
import asyncio
import os
import tempfile
from typing import Optional
import json

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

import yt_dlp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caption import VideoCaption
from app.models.competitor import CompetitorVideo
from app.core.config import settings

logger = logging.getLogger(__name__)


class SubtitleService:
    """
    yt-dlp 기반 YouTube 자막 추출 서비스.
    
    공식 가이드 참고:
    - CLI: yt-dlp --write-auto-subs URL
    - API: ydl_opts = {'writeautomaticsub': True}
    """

    _last_request_time: float = 0
    _MIN_INTERVAL = 2.0
    _proxy_rr_idx: int = 0

    # ── 프록시 관리 ──────────────────────────────────────

    @staticmethod
    def _get_proxy_pool() -> list[str]:
        """ENV에서 프록시 풀 파싱."""
        import re
        raw = (settings.youtube_proxy_url or "").strip()
        if not raw:
            return []
        return [p.strip() for p in re.split(r"[,\n;]+", raw) if p.strip()]

    @staticmethod
    def _pick_proxy() -> Optional[str]:
        """라운드로빈으로 프록시 선택."""
        pool = SubtitleService._get_proxy_pool()
        if not pool:
            return None
        picked = pool[SubtitleService._proxy_rr_idx % len(pool)]
        SubtitleService._proxy_rr_idx += 1
        return picked

    @staticmethod
    def _redact_proxy(proxy_url: str) -> str:
        """로그용 프록시 마스킹."""
        import re
        return re.sub(r"(https?://[^:]+):[^@]+@", r"\1:***@", proxy_url)

    # ── Rate Limiting ──────────────────────────────────────

    @staticmethod
    async def _throttle():
        """요청 간 최소 간격 보장."""
        elapsed = time.time() - SubtitleService._last_request_time
        wait = SubtitleService._MIN_INTERVAL - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        SubtitleService._last_request_time = time.time()

    # ── 핵심: 자막 추출 (youtube-transcript-api 우선, yt-dlp 폴백) ──

    @staticmethod
    def _fetch_with_transcript_api(
        video_id: str,
        languages: list[str],
    ) -> dict:
        """
        youtube-transcript-api로 자막 가져오기.
        프록시/쿠키 불필요. 1순위 방법.
        """
        try:
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id, languages=languages)
            
            cues = []
            for snippet in transcript.snippets:
                cues.append({
                    "start": snippet.start,
                    "end": snippet.start + snippet.duration,
                    "text": snippet.text.strip(),
                })
            
            lang = (
                transcript.language_code
                if hasattr(transcript, 'language_code')
                else (languages[0] if languages else "und")
            )
            is_auto = transcript.is_generated if hasattr(transcript, 'is_generated') else False
            
            logger.info(
                f"[SUBTITLE] ✓ transcript-api 성공 [{video_id}] "
                f"lang={lang}, cues={len(cues)}"
            )
            return {
                "video_id": video_id,
                "status": "success",
                "source": "transcript-api",
                "tracks": [{
                    "language_code": lang,
                    "language_name": lang,
                    "is_auto_generated": is_auto,
                    "cues": cues,
                }],
                "no_captions": False,
                "error": None,
            }
        except TranscriptsDisabled:
            logger.info(f"[SUBTITLE] transcript-api: 자막 비활성화 [{video_id}]")
            return {"video_id": video_id, "status": "no_subtitle", "source": "transcript-api", "tracks": [], "no_captions": True, "error": None}
        except NoTranscriptFound:
            logger.info(f"[SUBTITLE] transcript-api: 해당 언어 자막 없음 [{video_id}]")
            return {"video_id": video_id, "status": "no_subtitle", "source": "transcript-api", "tracks": [], "no_captions": True, "error": None}
        except VideoUnavailable:
            logger.warning(f"[SUBTITLE] transcript-api: 영상 접근 불가 [{video_id}]")
            return {"video_id": video_id, "status": "failed", "source": "transcript-api", "tracks": [], "no_captions": True, "error": "Video unavailable"}
        except Exception as e:
            logger.warning(f"[SUBTITLE] transcript-api 실패 [{video_id}]: {type(e).__name__}: {e}")
            return {"video_id": video_id, "status": "failed", "source": "transcript-api", "tracks": [], "no_captions": True, "error": str(e)}

    @staticmethod
    async def fetch_subtitles(
        video_ids: list[str],
        languages: list[str],
        db: Optional[AsyncSession] = None,
    ) -> list[dict]:
        """
        자막 다운로드 (2단계 전략).
        
        1순위: youtube-transcript-api (프록시/쿠키 불필요)
        2순위: yt-dlp (프록시 사용, 폴백)
        
        Args:
            video_ids: YouTube 영상 ID 리스트
            languages: 우선순위 언어 코드 (예: ["ko", "en"])
            db: DB 세션 (자막 캐싱용)
        
        Returns:
            [{"video_id": "...", "status": "success", "tracks": [...]}]
        """
        results = []

        for video_id in video_ids:
            await SubtitleService._throttle()
            
            # ── 1순위: youtube-transcript-api ──
            result = await asyncio.to_thread(
                SubtitleService._fetch_with_transcript_api,
                video_id,
                languages,
            )
            
            cue_count = sum(len(t.get("cues", [])) for t in result.get("tracks", []))
            if result.get("status") == "success" and cue_count > 0:
                # 성공 → DB 저장 후 다음 영상
                results.append(result)
                if db is not None:
                    logger.info(f"[SUBTITLE] → DB 저장 시작 [{video_id}] cues={cue_count}")
                    await SubtitleService._save_caption(db, video_id, result)
                continue
            
            # 자막이 실제로 없는 경우 (비활성화 등) → yt-dlp 시도 불필요
            if result.get("no_captions") and not result.get("error"):
                results.append(result)
                continue
            
            # ── 2순위: yt-dlp 폴백 ──
            logger.info(f"[SUBTITLE] transcript-api 실패, yt-dlp 폴백 시도 [{video_id}]")
            proxy_pool = SubtitleService._get_proxy_pool()
            max_attempts = min(len(proxy_pool), 5) if proxy_pool else 3
            last_error = None

            for attempt in range(max_attempts):
                proxy_url = SubtitleService._pick_proxy() if proxy_pool else None
                
                try:
                    result = await asyncio.to_thread(
                        SubtitleService._fetch_subtitle_with_ytdlp,
                        video_id,
                        languages,
                        proxy_url
                    )
                    
                    cue_count = sum(len(t.get("cues", [])) for t in result.get("tracks", []))
                    if result.get("status") == "success" and cue_count > 0:
                        logger.info(
                            f"[SUBTITLE] ✓ yt-dlp 성공 [{video_id}] "
                            f"attempt={attempt+1}, cues={cue_count}"
                        )
                        break
                    
                    if result.get("no_captions") and not result.get("error"):
                        break
                    
                    err = result.get("error", "")
                    if "429" in err or "Too Many Requests" in err or "sign in" in err.lower():
                        last_error = err
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(2.0)
                            continue
                        
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"[SUBTITLE] ✗ yt-dlp 예외 [{video_id}] {type(e).__name__}: {e}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2.0)
                        continue
                    break

            # 최종 결과 처리
            if result is None:
                result = {
                    "video_id": video_id,
                    "status": "failed",
                    "source": "yt-dlp",
                    "tracks": [],
                    "no_captions": True,
                    "error": last_error or "Unknown error",
                }
                logger.error(f"[SUBTITLE] ✗ 최종 실패 [{video_id}] error={last_error}")
            elif result.get("status") == "failed" and not result.get("error"):
                result["error"] = last_error or "Unknown error"

            results.append(result)
            
            cue_count = sum(len(t.get("cues", [])) for t in result.get("tracks", []))
            if db is not None and result.get("status") == "success" and cue_count > 0:
                logger.info(f"[SUBTITLE] → DB 저장 시작 [{video_id}] cues={cue_count}")
                await SubtitleService._save_caption(db, video_id, result)

        return results

    @staticmethod
    def _fetch_subtitle_with_ytdlp(
        video_id: str,
        languages: list[str],
        proxy_url: Optional[str],
    ) -> dict:
        """
        yt-dlp로 자막 메타데이터만 추출 (download=False).
        
        전략:
        1. yt-dlp.extract_info(download=False) → 자막 URL만 가져오기
        2. httpx로 자막 직접 다운로드 (프록시 사용)
        3. JSON3 파싱
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        # yt-dlp 옵션 (메타데이터만 추출, 다운로드 안 함)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,  # 전체 메타데이터 추출
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'mweb'],
                },
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            },
        }

        # 프록시 설정
        if proxy_url:
            ydl_opts['proxy'] = proxy_url
            logger.info(
                f"[SUBTITLE] yt-dlp 프록시 [{video_id}]: "
                f"{SubtitleService._redact_proxy(proxy_url)}"
            )
        
        # 쿠키 설정 (선택사항)
        cookie_path = SubtitleService._get_cookie_path()
        if cookie_path:
            ydl_opts['cookiefile'] = cookie_path
            logger.info(f"[SUBTITLE] yt-dlp 쿠키 [{video_id}]: {cookie_path}")
        
        try:
            # 버전 로그 (최초 1회)
            if not hasattr(SubtitleService, '_ytdlp_version_logged'):
                logger.info(f"[SUBTITLE] yt-dlp version: {yt_dlp.version.__version__}")
                SubtitleService._ytdlp_version_logged = True
            
            logger.info(f"[SUBTITLE] yt-dlp 메타데이터 추출 시작 [{video_id}]")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # extract_info(download=False) → 자막 URL만 가져오기
                info = ydl.extract_info(url, download=False)
            
            if not info:
                return {
                    "video_id": video_id,
                    "status": "failed",
                    "source": "yt-dlp",
                    "tracks": [],
                    "no_captions": True,
                    "error": "Failed to extract video info",
                }
            
            # 자막 메타데이터 추출
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            logger.info(
                f"[SUBTITLE] 메타데이터 추출 완료 [{video_id}] "
                f"subtitles={list(subtitles.keys())}, "
                f"auto_captions={list(automatic_captions.keys())}"
            )
            
            # 언어 우선순위대로 시도
            for lang in languages:
                # 1) 수동 자막 우선
                if lang in subtitles:
                    subtitle_url = SubtitleService._get_json3_url(subtitles[lang])
                    if subtitle_url:
                        cues = SubtitleService._download_and_parse(subtitle_url, proxy_url)
                        if cues:
                            logger.info(
                                f"[SUBTITLE] ✓ 수동 자막 [{video_id}] "
                                f"lang={lang}, cues={len(cues)}"
                            )
                            return {
                                "video_id": video_id,
                                "status": "success",
                                "source": "yt-dlp",
                                "tracks": [{
                                    "language_code": lang,
                                    "language_name": lang,
                                    "is_auto_generated": False,
                                    "cues": cues,
                                }],
                                "no_captions": False,
                                "error": None,
                            }
                
                # 2) 자동생성 자막
                if lang in automatic_captions:
                    subtitle_url = SubtitleService._get_json3_url(automatic_captions[lang])
                    if subtitle_url:
                        cues = SubtitleService._download_and_parse(subtitle_url, proxy_url)
                        if cues:
                            logger.info(
                                f"[SUBTITLE] ✓ 자동생성 자막 [{video_id}] "
                                f"lang={lang}, cues={len(cues)}"
                            )
                            return {
                                "video_id": video_id,
                                "status": "success",
                                "source": "yt-dlp",
                                "tracks": [{
                                    "language_code": lang,
                                    "language_name": lang,
                                    "is_auto_generated": True,
                                    "cues": cues,
                                }],
                                "no_captions": False,
                                "error": None,
                            }
            
            # 자막 없음
            return {
                "video_id": video_id,
                "status": "no_subtitle",
                "source": "yt-dlp",
                "tracks": [],
                "no_captions": True,
                "error": None,
            }
        
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"[SUBTITLE] yt-dlp DownloadError [{video_id}]: {error_msg}")
            
            # 429나 sign in 에러는 프록시 전환으로 해결 가능
            if any(x in error_msg.lower() for x in ["429", "too many requests", "sign in"]):
                return {
                    "video_id": video_id,
                    "status": "failed",
                    "source": "yt-dlp",
                    "tracks": [],
                    "no_captions": True,
                    "error": "429 Too Many Requests",
                }
            
            return {
                "video_id": video_id,
                "status": "failed",
                "source": "yt-dlp",
                "tracks": [],
                "no_captions": True,
                "error": error_msg,
            }
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"[SUBTITLE] yt-dlp 예외 [{video_id}]: {error_msg}")
            return {
                "video_id": video_id,
                "status": "failed",
                "source": "yt-dlp",
                "tracks": [],
                "no_captions": True,
                "error": error_msg,
            }

    @staticmethod
    def _get_json3_url(subtitle_formats: list) -> Optional[str]:
        """
        자막 포맷 리스트에서 json3 URL 추출.
        
        yt-dlp 자막 형식:
        [
            {"ext": "srv3", "url": "https://..."},
            {"ext": "json3", "url": "https://..."},
            {"ext": "vtt", "url": "https://..."},
        ]
        """
        if not subtitle_formats or not isinstance(subtitle_formats, list):
            return None
        
        # json3 포맷 우선
        for fmt in subtitle_formats:
            if fmt.get('ext') == 'json3' and fmt.get('url'):
                return fmt['url']
        
        # json3 없으면 첫 번째 URL
        for fmt in subtitle_formats:
            if fmt.get('url'):
                return fmt['url']
        
        return None

    @staticmethod
    def _download_and_parse(subtitle_url: str, proxy_url: Optional[str]) -> list[dict]:
        """
        자막 URL을 httpx로 다운로드하고 파싱.
        
        이 함수는 동기 함수입니다 (asyncio.to_thread에서 호출).
        """
        import httpx
        
        try:
            logger.info(f"[SUBTITLE] 자막 URL 다운로드 시작: {subtitle_url[:80]}...")
            
            client_opts = {
                'timeout': 15.0,
                'follow_redirects': True,
            }
            if proxy_url:
                client_opts['proxy'] = proxy_url
                logger.info(f"[SUBTITLE] httpx 프록시 사용: {SubtitleService._redact_proxy(proxy_url)}")
            
            with httpx.Client(**client_opts) as client:
                resp = client.get(subtitle_url)
                resp.raise_for_status()
                content = resp.text
            
            logger.info(f"[SUBTITLE] 자막 다운로드 성공, size={len(content)}")
            
            # JSON3 파싱
            return SubtitleService._parse_json3(content)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"[SUBTITLE] 자막 다운로드 429: {subtitle_url[:80]}")
                raise  # 상위로 전파 → 프록시 전환
            logger.warning(f"[SUBTITLE] 자막 다운로드 HTTP 에러 {e.response.status_code}")
            return []
        except Exception as e:
            logger.warning(f"[SUBTITLE] 자막 다운로드 실패: {e}")
            return []

    @staticmethod
    def _get_cookie_path() -> Optional[str]:
        """
        쿠키 파일 절대 경로 반환 및 검증.
        
        yt-dlp 쿠키 요구사항 (공식 FAQ):
        - Mozilla/Netscape 형식
        - 첫 줄: # HTTP Cookie File 또는 # Netscape HTTP Cookie File
        - Windows: CRLF newline (\r\n)
        """
        cookie_path = settings.youtube_cookies_file
        
        if not cookie_path:
            logger.warning("[SUBTITLE] ENV에 YOUTUBE_COOKIES_FILE이 설정되지 않음")
            return None
        
        # 절대 경로면 그대로 사용
        if os.path.isabs(cookie_path):
            abs_path = os.path.normpath(cookie_path)  # 경로 정규화
        else:
            # 상대 경로면 BE 디렉토리 기준으로 변환
            # __file__ = BE/app/services/subtitle_service.py
            # BE 디렉토리 = dirname(dirname(dirname(__file__)))
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            abs_path = os.path.normpath(os.path.join(base_dir, cookie_path))
        
        # 파일 존재 확인
        if not os.path.exists(abs_path):
            logger.warning(f"[SUBTITLE] 쿠키 파일 없음: {abs_path}")
            return None
        
        # 파일 형식 검증
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                
            valid_headers = ['# HTTP Cookie File', '# Netscape HTTP Cookie File']
            if not any(first_line.startswith(h) for h in valid_headers):
                logger.warning(
                    f"[SUBTITLE] 쿠키 파일 형식 오류: "
                    f"첫 줄이 Netscape 형식이 아님. first_line='{first_line}'"
                )
                return None
            
            logger.info(f"[SUBTITLE] ✓ 쿠키 파일 검증 완료: {abs_path}")
            return abs_path
            
        except Exception as e:
            logger.warning(f"[SUBTITLE] 쿠키 파일 검증 실패: {e}")
            return None

    @staticmethod
    def _parse_json3(json_content: str) -> list[dict]:
        """
        YouTube JSON3 형식 파싱.
        
        구조:
        {
            "events": [
                {
                    "tStartMs": 0,
                    "dDurationMs": 2500,
                    "segs": [{"utf8": "안녕하세요"}]
                }
            ]
        }
        """
        try:
            data = json.loads(json_content)
            events = data.get('events', [])
            
            cues = []
            for event in events:
                t_start_ms = event.get('tStartMs', 0)
                d_duration_ms = event.get('dDurationMs', 0)
                segs = event.get('segs', [])
                
                if not segs:
                    continue
                
                # 여러 세그먼트를 하나의 텍스트로 합침
                text = ''.join(seg.get('utf8', '') for seg in segs).strip()
                
                if text:
                    cues.append({
                        "start": t_start_ms / 1000.0,
                        "end": (t_start_ms + d_duration_ms) / 1000.0,
                        "text": text,
                    })
            
            logger.info(f"[SUBTITLE] JSON3 파싱 완료: cues={len(cues)}")
            return cues
            
        except Exception as e:
            logger.warning(f"[SUBTITLE] JSON3 파싱 실패: {e}")
            return []

    # ── DB 저장 ──────────────────────────────────────

    @staticmethod
    async def _save_caption(
        db: AsyncSession,
        youtube_video_id: str,
        result: dict,
    ) -> None:
        """자막을 DB에 저장 (CompetitorVideo와 연결)."""
        try:
            cue_total = sum(len(t.get("cues", [])) for t in result.get("tracks", []))
            if result.get("status") != "success" or cue_total == 0:
                logger.warning(
                    f"[SUBTITLE] DB 저장 실패 조건 [{youtube_video_id}] "
                    f"status={result.get('status')}, cues={cue_total}"
                )
                return

            # CompetitorVideo 조회
            stmt = (
                select(CompetitorVideo)
                .where(CompetitorVideo.youtube_video_id == youtube_video_id)
                .limit(1)
            )
            row = await db.execute(stmt)
            comp_video = row.scalar_one_or_none()

            if comp_video is None:
                logger.warning(f"[SUBTITLE] CompetitorVideo 없음, 저장 스킵 [{youtube_video_id}]")
                return

            logger.debug(
                f"[SUBTITLE] CompetitorVideo 발견 [{youtube_video_id}] "
                f"id={comp_video.id}"
            )

            # 기존 자막 조회
            stmt2 = select(VideoCaption).where(
                VideoCaption.competitor_video_id == comp_video.id
            )
            row2 = await db.execute(stmt2)
            existing = row2.scalar_one_or_none()

            # 저장할 데이터
            segments_data = {
                "source": result.get("source", "yt-dlp"),
                "tracks": result.get("tracks", []),
                "no_captions": result.get("no_captions", False),
            }

            # Update or Insert
            if existing:
                logger.info(
                    f"[SUBTITLE] video_captions 업데이트 [{youtube_video_id}] "
                    f"caption_id={existing.id}, tracks={len(segments_data['tracks'])}, cues={cue_total}"
                )
                existing.segments_json = segments_data
            else:
                logger.info(
                    f"[SUBTITLE] video_captions 신규 생성 [{youtube_video_id}] "
                    f"competitor_video_id={comp_video.id}, tracks={len(segments_data['tracks'])}, cues={cue_total}"
                )
                caption = VideoCaption(
                    competitor_video_id=comp_video.id,
                    segments_json=segments_data,
                )
                db.add(caption)

            await db.commit()
            logger.info(f"[SUBTITLE] ✓ DB 커밋 완료 [{youtube_video_id}] → video_captions 테이블")
            
        except Exception as e:
            logger.error(f"[SUBTITLE] ✗ DB 저장 예외 [{youtube_video_id}]: {type(e).__name__}: {e}")
            await db.rollback()
