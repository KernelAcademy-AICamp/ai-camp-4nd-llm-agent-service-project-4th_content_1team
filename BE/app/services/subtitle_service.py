import logging
import re
import json
import time
import asyncio
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

from app.models.caption import VideoCaption
from app.models.competitor import CompetitorVideo
from app.core.config import settings

logger = logging.getLogger(__name__)


class SubtitleService:

    _last_request_time: float = 0
    _MIN_INTERVAL = 5.0  # 3초 → 5초로 증가 (Rate Limiting 강화)

    # ── Public API ──────────────────────────────────────

    @staticmethod
    async def fetch_subtitles(
        video_ids: list[str],
        languages: list[str],
        db: Optional[AsyncSession] = None,
    ) -> list[dict]:
        results = []
        for video_id in video_ids:
            await SubtitleService._throttle()
            result = await SubtitleService._fetch_innertube(video_id, languages)
            results.append(result)
            if db is not None:
                await SubtitleService._save_caption(db, video_id, result)
        return results

    # ── Private: Innertube pipeline ─────────────────────

    @staticmethod
    async def _fetch_innertube(video_id: str, languages: list[str]) -> dict:
        """Innertube API로 자막 트랙을 가져와 파싱 (1차 시도)."""
        try:
            player_response = await SubtitleService._fetch_player_response(video_id)
            tracks_meta = SubtitleService._extract_caption_tracks(player_response)

            if not tracks_meta:
                logger.warning(f"Innertube에서 자막 트랙 없음, 라이브러리로 폴백 [{video_id}]")
                # 폴백: youtube-transcript-api로 재시도 (Cookies/Proxy 사용)
                return await SubtitleService._fetch_with_library(
                    video_id,
                    languages,
                    cookies=settings.youtube_cookies_file,
                    proxies=SubtitleService._get_proxy_config()
                )

            # 필터: 요청된 언어만
            filtered = [
                t for t in tracks_meta
                if t["language_code"] in languages
            ]
            if not filtered:
                filtered = tracks_meta  # 없으면 전부

            tracks = []
            for meta in filtered:
                content = await SubtitleService._download_subtitle_track(meta["base_url"])
                cues = SubtitleService._parse_subtitle(content)
                tracks.append({
                    "language_code": meta["language_code"],
                    "language_name": meta["language_name"],
                    "is_auto_generated": meta["is_auto_generated"],
                    "cues": cues,
                })
                await asyncio.sleep(0.5)  # 트랙 간 짧은 딜레이

            return {
                "video_id": video_id,
                "status": "success",
                "source": "innertube",
                "tracks": tracks,
                "no_captions": False,
                "error": None,
            }

        except Exception as e:
            logger.warning(f"Innertube 자막 조회 실패, 라이브러리로 폴백 [{video_id}]: {e}")
            # 폴백: youtube-transcript-api로 재시도 (Cookies/Proxy 사용)
            return await SubtitleService._fetch_with_library(
                video_id,
                languages,
                cookies=settings.youtube_cookies_file,
                proxies=SubtitleService._get_proxy_config()
            )

    @staticmethod
    async def _fetch_player_response(video_id: str) -> dict:
        """YouTube watch page에서 ytInitialPlayerResponse JSON 추출."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        html = resp.text

        # ytInitialPlayerResponse 시작 위치 찾기
        marker = "ytInitialPlayerResponse"
        idx = html.find(marker)
        if idx == -1:
            raise ValueError(f"ytInitialPlayerResponse를 찾을 수 없음: {video_id}")

        # '=' 이후 '{' 시작 위치 찾기
        eq_idx = html.index("=", idx)
        brace_start = html.index("{", eq_idx)

        # brace counting으로 전체 JSON 객체 추출
        depth = 0
        i = brace_start
        while i < len(html):
            ch = html[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            elif ch == '"':
                # 문자열 내부 스킵 (escape 처리)
                i += 1
                while i < len(html) and html[i] != '"':
                    if html[i] == "\\":
                        i += 1  # escape 다음 문자 스킵
                    i += 1
            i += 1

        json_str = html[brace_start:i + 1]
        return json.loads(json_str)

    @staticmethod
    def _extract_caption_tracks(player_response: dict) -> list[dict]:
        """playerResponse에서 captionTracks 추출."""
        try:
            caption_tracks = (
                player_response
                .get("captions", {})
                .get("playerCaptionsTracklistRenderer", {})
                .get("captionTracks", [])
            )
        except (KeyError, AttributeError):
            return []

        results = []
        for track in caption_tracks:
            lang_code = track.get("languageCode", "")
            kind = track.get("kind", "")
            name_obj = track.get("name", {})
            # name can be {runs: [{text: "..."}]} or {simpleText: "..."}
            if "runs" in name_obj:
                lang_name = name_obj["runs"][0].get("text", lang_code)
            else:
                lang_name = name_obj.get("simpleText", lang_code)

            results.append({
                "base_url": track["baseUrl"],
                "language_code": lang_code,
                "language_name": lang_name,
                "is_auto_generated": kind == "asr",
            })

        return results

    @staticmethod
    async def _download_subtitle_track(base_url: str) -> str:
        """baseUrl로 WebVTT 자막 다운로드. fmt를 강제로 vtt로 설정."""
        # 기존 fmt 파라미터를 vtt로 교체
        url = re.sub(r"[&?]fmt=[^&]*", "", base_url)
        url += "&fmt=vtt"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.text

        # VTT가 아닌 XML이 반환된 경우 srv3 XML로 재시도 후 XML 파싱
        if content.strip().startswith("<?xml") or content.strip().startswith("<transcript"):
            logger.warning("VTT 요청했으나 XML 반환됨, srv3로 재시도")
            url2 = re.sub(r"[&?]fmt=[^&]*", "", base_url) + "&fmt=srv3"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp2 = await client.get(url2)
                resp2.raise_for_status()
                return "XML:" + resp2.text  # prefix로 XML 구분

        return content

    @staticmethod
    def _parse_subtitle(content: str) -> list[dict]:
        """VTT 또는 XML(srv3) 자막을 {start, end, text} 리스트로 파싱."""
        if content.startswith("XML:"):
            return SubtitleService._parse_srv3_xml(content[4:])
        return SubtitleService._parse_vtt(content)

    @staticmethod
    def _parse_vtt(vtt_content: str) -> list[dict]:
        """WebVTT를 {start, end, text} 리스트로 파싱."""
        cues = []
        pattern = re.compile(
            r"(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})"
        )

        lines = vtt_content.split("\n")
        i = 0
        while i < len(lines):
            match = pattern.match(lines[i].strip())
            if match:
                start = SubtitleService._vtt_time_to_seconds(match.group(1))
                end = SubtitleService._vtt_time_to_seconds(match.group(2))
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                text = " ".join(text_lines)
                # Strip VTT tags like <c>, </c>, inline timestamps
                text = re.sub(r"<[^>]+>", "", text)
                text = text.strip()
                if text:
                    cues.append({"start": start, "end": end, "text": text})
            else:
                i += 1

        return cues

    @staticmethod
    def _parse_srv3_xml(xml_content: str) -> list[dict]:
        """YouTube srv3 XML 자막을 파싱. <text start="0.0" dur="2.5">텍스트</text>"""
        import html
        cues = []
        pattern = re.compile(
            r'<text\s+start="([\d.]+)"\s+dur="([\d.]+)"[^>]*>(.*?)</text>',
            re.DOTALL,
        )
        for m in pattern.finditer(xml_content):
            start = float(m.group(1))
            dur = float(m.group(2))
            text = html.unescape(m.group(3))
            text = re.sub(r"<[^>]+>", "", text).strip()
            if text:
                cues.append({"start": start, "end": round(start + dur, 3), "text": text})
        return cues

    @staticmethod
    def _vtt_time_to_seconds(time_str: str) -> float:
        """HH:MM:SS.mmm -> float seconds."""
        h, m, rest = time_str.split(":")
        s, ms = rest.split(".")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    # ── Private: Rate Limiting ─────────────────────────

    @staticmethod
    async def _throttle():
        elapsed = time.time() - SubtitleService._last_request_time
        wait = SubtitleService._MIN_INTERVAL - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        SubtitleService._last_request_time = time.time()

    # ── Private: DB 저장 ───────────────────────────────

    @staticmethod
    async def _save_caption(
        db: AsyncSession,
        youtube_video_id: str,
        result: dict,
    ) -> None:
        try:
            stmt = select(CompetitorVideo).where(
                CompetitorVideo.youtube_video_id == youtube_video_id
            )
            row = await db.execute(stmt)
            comp_video = row.scalar_one_or_none()

            if comp_video is None:
                logger.debug(f"CompetitorVideo 없음, 저장 스킵: {youtube_video_id}")
                return

            stmt2 = select(VideoCaption).where(
                VideoCaption.competitor_video_id == comp_video.id
            )
            row2 = await db.execute(stmt2)
            existing = row2.scalar_one_or_none()

            segments_data = {
                "source": result.get("source", "unknown"),  # innertube 또는 library
                "tracks": result.get("tracks", []),
                "no_captions": result.get("no_captions", False),
            }

            if existing:
                existing.segments_json = segments_data
            else:
                caption = VideoCaption(
                    competitor_video_id=comp_video.id,
                    segments_json=segments_data,
                )
                db.add(caption)

            await db.commit()
            logger.info(f"자막 DB 저장 완료 [{youtube_video_id}]")
        except Exception as e:
            logger.error(f"자막 DB 저장 실패 [{youtube_video_id}]: {e}")
            await db.rollback()

    # ── Private: youtube-transcript-api 라이브러리 사용 ─────

    @staticmethod
    async def _fetch_with_library(
        video_id: str,
        languages: list[str],
        cookies: Optional[str] = None,
        proxies: Optional[dict] = None
    ) -> dict:
        """
        youtube-transcript-api 라이브러리로 자막 추출 (2차 시도).
        
        언어 폴백 전략:
        1. 요청한 언어의 수동 자막
        2. 요청한 언어의 자동 생성 자막
        3. 모든 언어의 수동 자막
        4. 모든 언어의 자동 생성 자막
        5. 없음 → no_captions: true
        
        Args:
            cookies: YouTube cookies 파일 경로 (선택, 429 에러 방지)
            proxies: 프록시 딕셔너리 (선택, IP 차단 회피)
        """
        try:
            # Cookies 및 Proxies 설정
            kwargs = {}
            if cookies:
                logger.info(f"Cookies 파일 사용: {cookies}")
                kwargs['cookies'] = cookies
            if proxies:
                logger.info(f"Proxy 사용: {proxies}")
                kwargs['proxies'] = proxies
            
            # 디버깅: 설정 확인
            logger.info(f"youtube-transcript-api 호출 [{video_id}] - kwargs: {list(kwargs.keys())}")
            
            transcript_list = YouTubeTranscriptApi.list_transcripts(
                video_id,
                **kwargs
            )
            
            # 1. 수동 자막 우선 (요청 언어)
            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
                cues = transcript.fetch()
                logger.info(f"수동 자막 발견 [{video_id}]: {transcript.language_code}")
                return SubtitleService._format_library_result(
                    video_id,
                    cues,
                    transcript.language_code,
                    transcript.language,
                    is_auto=False
                )
            except NoTranscriptFound:
                logger.debug(f"요청 언어의 수동 자막 없음 [{video_id}]")
            
            # 2. 자동 생성 자막 (요청 언어)
            try:
                transcript = transcript_list.find_generated_transcript(languages)
                cues = transcript.fetch()
                logger.info(f"자동 생성 자막 발견 [{video_id}]: {transcript.language_code}")
                return SubtitleService._format_library_result(
                    video_id,
                    cues,
                    transcript.language_code,
                    transcript.language,
                    is_auto=True
                )
            except NoTranscriptFound:
                logger.debug(f"요청 언어의 자동 자막 없음 [{video_id}]")
            
            # 3. 모든 수동 자막
            for transcript in transcript_list:
                if not transcript.is_generated:
                    cues = transcript.fetch()
                    logger.info(f"다른 언어 수동 자막 발견 [{video_id}]: {transcript.language_code}")
                    return SubtitleService._format_library_result(
                        video_id,
                        cues,
                        transcript.language_code,
                        transcript.language,
                        is_auto=False
                    )
            
            # 4. 모든 자동 생성 자막
            for transcript in transcript_list:
                if transcript.is_generated:
                    cues = transcript.fetch()
                    logger.info(f"다른 언어 자동 자막 발견 [{video_id}]: {transcript.language_code}")
                    return SubtitleService._format_library_result(
                        video_id,
                        cues,
                        transcript.language_code,
                        transcript.language,
                        is_auto=True
                    )
            
            # 5. 정말 자막 없음
            logger.warning(f"자막이 전혀 없음 [{video_id}]")
            return {
                "video_id": video_id,
                "status": "no_subtitle",
                "source": "library",
                "tracks": [],
                "no_captions": True,
                "error": None
            }
                
        except TranscriptsDisabled:
            logger.warning(f"자막 비활성화 [{video_id}]")
            return {
                "video_id": video_id,
                "status": "no_subtitle",
                "source": "library",
                "tracks": [],
                "no_captions": True,
                "error": "자막이 비활성화되어 있습니다"
            }
        except VideoUnavailable:
            logger.error(f"비디오 없음 [{video_id}]")
            return {
                "video_id": video_id,
                "status": "failed",
                "source": "library",
                "tracks": [],
                "no_captions": True,
                "error": "비디오를 찾을 수 없습니다"
            }
        except Exception as e:
            logger.error(f"라이브러리 자막 조회 실패 [{video_id}]: {e}")
            return {
                "video_id": video_id,
                "status": "failed",
                "source": "library",
                "tracks": [],
                "no_captions": True,
                "error": str(e)
            }
    
    @staticmethod
    def _format_library_result(
        video_id: str,
        cues: list,
        language_code: str,
        language_name: str,
        is_auto: bool
    ) -> dict:
        """
        youtube-transcript-api 결과를 통일된 포맷으로 변환.
        
        라이브러리 포맷: [{"text": "...", "start": 0.0, "duration": 2.5}]
        우리 포맷: [{"text": "...", "start": 0.0, "end": 2.5}]
        """
        formatted_cues = []
        for cue in cues:
            formatted_cues.append({
                "start": cue["start"],
                "end": cue["start"] + cue["duration"],
                "text": cue["text"]
            })
        
        logger.info(f"자막 변환 완료 [{video_id}]: {len(formatted_cues)}개 세그먼트")
        
        return {
            "video_id": video_id,
            "status": "success",
            "source": "library",
            "tracks": [{
                "language_code": language_code,
                "language_name": language_name,
                "is_auto_generated": is_auto,
                "cues": formatted_cues
            }],
            "no_captions": False,
            "error": None
        }
    
    @staticmethod
    def _get_proxy_config() -> Optional[dict]:
        """
        환경 변수에서 Proxy 설정 가져오기.
        
        Returns:
            {"http": "...", "https": "..."} 또는 None
        """
        if not settings.youtube_proxy_url:
            return None
        
        return {
            "http": settings.youtube_proxy_url,
            "https": settings.youtube_proxy_url
        }
