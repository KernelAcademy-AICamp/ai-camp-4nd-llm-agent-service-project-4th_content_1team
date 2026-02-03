# 자막 불러오기 → 분석까지 개발 과정 정리

경쟁 영상 "상세 정보 보기" 클릭 시, 해당 영상 자막을 가져와 LLM으로 분석하여 핵심 내용·장점·부족한 점을 표시하는 기능의 개발 과정을 정리한 문서입니다.

---

## 1. 최종 아키텍처 (성공 버전)

```
[FE] 상세 정보 보기 클릭
  → POST /api/v1/competitor/analyze {youtube_video_id}
    → [BE] CompetitorService.analyze_video_content()
      → 1) CompetitorVideo 조회
      → 2) VideoContentAnalysis 캐시 조회 (있으면 바로 반환)
      → 3) SubtitleService.fetch_subtitles() 로 자막 조회
        → yt-dlp.extract_info(download=False) : 자막 URL만 추출
        → httpx로 자막 다운로드 (프록시 사용)
        → JSON3 파싱 → video_captions 테이블 저장
      → 4) 자막 텍스트 → OpenAI gpt-4o-mini 분석
      → 5) VideoContentAnalysis 저장 후 반환
```

---

## 2. 시도한 방법들과 겪었던 문제

### 2-1. downsub 방식 (직접 timedtext API 호출)

**시도한 것**
- `https://www.youtube.com/api/timedtext?v={VIDEO_ID}&lang=ko` 직접 호출
- XML 파싱 후 DB 저장

**발생한 문제**
- 200 OK인데 `content_length=0` → YouTube 봇 탐지로 빈 응답
- 429 Too Many Requests
- 프록시 사용해도 동일

### 2-2. Innertube 방식 (watch 페이지 파싱)

**시도한 것**
- watch 페이지에서 `ytInitialPlayerResponse` 파싱
- `captionTracks.baseUrl` 추출 후 timedtext 다운로드
- VTT/JSON3/SRV3 다중 포맷 파싱
- youtube-transcript-api 라이브러리 폴백

**발생한 문제**
- watch와 timedtext 요청 시 **프록시 계정이 달라** 404 발생 (세션 불일치)
- timedtext 요청 시 429
- 쿠키 파일 경로 오류 (`be/app/config` vs `BE/config`)

### 2-3. yt-dlp download() 방식

**시도한 것**
- `ydl_opts = {'writeautomaticsub': True, 'skip_download': True}`
- `ydl.download([url])` → 자막 파일 자동 다운로드
- 임시 디렉토리에 저장된 `.json3` 파일 파싱

**발생한 문제**
- "Please sign in" (쿠키 인식 실패)
- Chrome `--cookies-from-browser` → Windows에서 "Could not copy Chrome cookie database"
- 쿠키 파일 사용 시에도 "Please sign in" (만료 또는 형식 문제)
- `subtitleslangs: ['all']` 사용 시 → 자막 다운로드 중 429

---

## 3. 최종 성공 전략 (B안)

### 핵심 아이디어

**yt-dlp는 메타데이터만 추출하고, 실제 다운로드는 우리가 httpx로 수행한다.**

| 단계 | 담당 | 목적 |
|------|------|------|
| 1 | yt-dlp.extract_info(download=False) | 자막 URL만 추출 (파일 다운로드 X) |
| 2 | httpx.get(url, proxy=...) | 자막 실제 다운로드 (프록시 사용) |
| 3 | _parse_json3() | JSON3 → cues 변환 |
| 4 | _save_caption() | video_captions 테이블 저장 |

### 쿠키 정책

- **쿠키 없이도 공개 영상 자막은 가능**
- 쿠키 파일은 선택 사항 (`.env`에서 주석 가능)
- Netscape 형식, 첫 줄: `# Netscape HTTP Cookie File`
- Windows: CRLF newline 권장 (yt-dlp FAQ)

### 프록시 정책

- `YOUTUBE_PROXY_URL`에 여러 프록시를 콤마로 구분하여 설정
- 429 발생 시 자동으로 다음 프록시로 전환 (최대 5회)
- 영상 1건당 동일 프록시 유지 (watch↔timedtext 세션 일치)

### 언어 요청 최소화

- `languages=["ko", "en"]` 만 사용 (429 방지)
- 첫 번째 성공한 자막에서 즉시 종료

---

## 4. 주요 파일 및 역할

| 파일 | 역할 |
|------|------|
| `app/services/subtitle_service.py` | yt-dlp + httpx 기반 자막 추출, DB 저장 |
| `app/services/competitor_service.py` | 자막 조회, LLM 분석, VideoContentAnalysis 생성 |
| `app/models/video_content_analysis.py` | 분석 결과 모델 (summary, strengths, weaknesses) |
| `app/models/caption.py` | VideoCaption (segments_json) |
| `config/youtube_cookies.txt` | Netscape 형식 쿠키 (선택) |

---

## 5. 환경 변수

```env
# 필수
OPENAI_API_KEY=sk-...

# 자막용 (선택)
YOUTUBE_PROXY_URL=http://user:pass@proxy:80,http://user2:pass2@proxy:80
YOUTUBE_COOKIES_FILE=config/youtube_cookies.txt
```

---

## 6. 성공 요약

1. **yt-dlp.extract_info(download=False)** → 자막 URL만 가져와 429 위험 감소
2. **httpx + 프록시** → 실제 다운로드는 우리가 제어
3. **429 시 프록시 전환** → 여러 프록시 풀 활용
4. **쿠키 없이 가능** → 공개 영상은 쿠키 불필요
5. **언어 최소화** → ko, en 만 요청해 요청 수 감소

---

## 7. 참고 링크

- [yt-dlp FAQ - How do I pass cookies](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
- [yt-dlp CLI to API](https://github.com/yt-dlp/yt-dlp/blob/master/devscripts/cli_to_api.py)
- [youtube-subtitle-setup.md](./youtube-subtitle-setup.md) (프로젝트 내 설정 가이드)
