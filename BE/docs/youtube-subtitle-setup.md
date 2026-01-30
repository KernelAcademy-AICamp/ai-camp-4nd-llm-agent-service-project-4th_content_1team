# YouTube 자막 다운로드 설정 가이드

## 문제: YouTube Rate Limiting (429 에러)

YouTube는 과도한 요청을 차단하여 429 에러를 발생시킵니다. 이를 해결하기 위해 **Cookies** 또는 **Proxy**를 사용해야 합니다.

---

## 해결 방법 1: YouTube Cookies 사용 (권장)

### 1-1. Cookies 추출

#### Chrome/Edge 사용 시

1. **확장 프로그램 설치**
   - [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - 또는 [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg)

2. **YouTube 로그인**
   - [YouTube](https://www.youtube.com)에 로그인

3. **Cookies 추출**
   - 확장 프로그램 아이콘 클릭
   - "Export" 클릭
   - Netscape 형식으로 저장

4. **파일 저장**
   ```
   BE/config/youtube_cookies.txt
   ```

### 1-2. 환경 변수 설정

`.env` 파일:
```env
YOUTUBE_COOKIES_FILE=config/youtube_cookies.txt
```

### 1-3. Cookies 파일 형식 예시

```txt
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1769783194	VISITOR_INFO1_LIVE	xxxxx
.youtube.com	TRUE	/	FALSE	1769783194	CONSENT	YES+xxx
.youtube.com	TRUE	/	TRUE	1769783194	SID	xxxxx
```

---

## 해결 방법 2: Proxy 서비스 사용

### 2-1. Webshare.io Proxy (무료 5개)

1. **가입**
   - [Webshare.io](https://www.webshare.io/) 접속
   - 무료 계정 생성 (5개 프록시 + 1GB/월)

2. **Proxy 정보 확인**
   - Dashboard → Proxy List
   - 주소, 포트, 인증 정보 복사

3. **환경 변수 설정**
   ```env
   YOUTUBE_PROXY_URL=http://username:password@proxy.webshare.io:9999
   ```

### 2-2. 다른 Proxy 서비스

| 서비스 | 무료 제공 | 특징 |
|--------|-----------|------|
| Webshare.io | 5개 프록시, 1GB | 추천 |
| Bright Data | 체험판 | 대용량 |
| Smartproxy | 체험판 | 고품질 |

---

## 해결 방법 3: Cookies + Proxy 조합 (최강)

**가장 안정적인 방법**:

```env
YOUTUBE_COOKIES_FILE=config/youtube_cookies.txt
YOUTUBE_PROXY_URL=http://user:pass@proxy:port
```

---

## 사용 방법

### 설정 후 자막 다운로드 테스트

```bash
cd BE
.\venv\Scripts\activate

# 단일 비디오 테스트
python test_has_caption_videos.py

# 대량 재처리
python scripts/reprocess_subtitles.py --limit 50
```

### API 호출

이제 자동으로 Cookies/Proxy를 사용합니다:

```python
# 자동으로 settings.youtube_cookies_file과 
# settings.youtube_proxy_url을 사용
POST /api/v1/subtitle/fetch
{
  "video_ids": ["video_id"],
  "languages": ["ko", "en"]
}
```

---

## 주의사항

### Cookies 사용 시
- ⚠️ Cookies는 주기적으로 만료됩니다 (재추출 필요)
- ⚠️ 공개 저장소에 Cookies 파일 커밋 금지
- ⚠️ `.gitignore`에 추가:
  ```
  config/youtube_cookies.txt
  *.cookies.txt
  ```

### Proxy 사용 시
- ✅ IP 로테이션으로 차단 회피
- ✅ 안정적인 대량 처리
- ⚠️ 유료 서비스 비용 발생 가능

---

## 트러블슈팅

### 429 에러가 계속 발생하는 경우

1. **Cookies 재추출**
   - 브라우저에서 로그아웃 후 재로그인
   - Cookies 다시 추출

2. **Proxy 변경**
   - 다른 Proxy 서버로 전환
   - Webshare에서 새 프록시 선택

3. **Rate Limiting 강화**
   [`subtitle_service.py:23`](../app/services/subtitle_service.py)
   ```python
   _MIN_INTERVAL = 10.0  # 5초 → 10초로 증가
   ```

4. **VPN 사용**
   - 임시로 VPN을 켜서 IP 변경
   - 테스트 후 Cookies 추출

---

## 설정 확인

### Cookies 파일 검증
```bash
# Cookies 파일 존재 확인
ls config/youtube_cookies.txt

# 내용 확인 (첫 5줄)
head -5 config/youtube_cookies.txt
```

### 설정 로드 확인
```python
from app.core.config import settings

print(f"Cookies: {settings.youtube_cookies_file}")
print(f"Proxy: {settings.youtube_proxy_url}")
```

---

## 성공 기준

✅ **Cookies 또는 Proxy 설정 완료**
✅ **429 에러 없이 자막 다운로드 성공**
✅ **DB에 자막 데이터 저장됨** (`tracks: [...]`)
✅ **자동 생성 자막 포함**
