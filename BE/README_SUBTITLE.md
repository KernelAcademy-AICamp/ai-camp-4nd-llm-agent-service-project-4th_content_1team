# YouTube 자막 다운로드 - Cookies/Proxy 설정 가이드

## 🚨 문제: 429 Too Many Requests

YouTube가 과도한 요청을 차단하여 자막 다운로드가 실패합니다.

## ✅ 해결 방법

### 옵션 1: YouTube Cookies 사용 (가장 간단)

#### 1단계: Cookies 추출

1. **Chrome 확장 프로그램 설치**
   - [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)

2. **YouTube 로그인**
   - https://www.youtube.com 접속
   - 계정 로그인

3. **Cookies 내보내기**
   - 확장 프로그램 아이콘 클릭
   - "Export" 또는 "Get Cookies" 클릭
   - `youtube_cookies.txt` 파일로 저장

4. **파일 저장 위치**
   ```
   BE/config/youtube_cookies.txt
   ```

#### 2단계: 환경 변수 설정

`.env` 파일:
```env
YOUTUBE_COOKIES_FILE=config/youtube_cookies.txt
```

---

### 옵션 2: Proxy 서비스 사용

#### Webshare.io (무료 5개 프록시)

1. **가입**
   - https://www.webshare.io 접속
   - 무료 계정 생성

2. **Proxy 정보 복사**
   - Dashboard → Proxy List
   - 주소: `proxy.webshare.io:9999`
   - 인증: username, password

3. **환경 변수 설정**
   ```env
   YOUTUBE_PROXY_URL=http://username:password@proxy.webshare.io:9999
   ```

---

### 옵션 3: Cookies + Proxy 조합 (최강)

```env
YOUTUBE_COOKIES_FILE=config/youtube_cookies.txt
YOUTUBE_PROXY_URL=http://username:password@proxy.webshare.io:9999
```

---

## 🧪 테스트

### 1. Cookies 파일 확인
```bash
# 파일 존재 여부
ls config/youtube_cookies.txt

# 첫 몇 줄 확인
head -5 config/youtube_cookies.txt
```

### 2. 설정 로드 확인
```bash
python -c "from app.core.config import settings; print('Cookies:', settings.youtube_cookies_file); print('Proxy:', settings.youtube_proxy_url)"
```

### 3. 자막 다운로드 테스트
```bash
# has_caption=true인 비디오 테스트
python test_has_caption_videos.py

# 성공하면 대량 재처리
python scripts/reprocess_subtitles.py --limit 50
```

---

## 📁 디렉토리 구조

```
BE/
├── config/
│   └── youtube_cookies.txt    # Cookies 파일
├── .env                        # 환경 변수
├── .env.example                # 환경 변수 템플릿
└── scripts/
    └── reprocess_subtitles.py  # 재처리 스크립트
```

---

## ⚠️ 보안 주의사항

### .gitignore 추가 (필수)

`.gitignore`:
```
# YouTube Cookies (보안)
config/youtube_cookies.txt
*.cookies.txt
cookies/
```

### Cookies 관리
- ❌ **절대 Git에 커밋하지 마세요**
- ❌ **공개 저장소에 업로드 금지**
- ✅ 로컬에만 보관
- ✅ 주기적으로 재추출 (만료 시)

---

## 🔄 자막 재처리 실행

### 전체 재처리
```bash
cd BE
.\venv\Scripts\activate

# 10개씩 처리 (안전)
python scripts/reprocess_subtitles.py --limit 10

# 30초 대기 후
python scripts/reprocess_subtitles.py --limit 10

# 반복...
```

### 대량 처리 (Proxy 사용 시)
```bash
# Proxy 설정 완료 후
python scripts/reprocess_subtitles.py --limit 100
```

---

## 📊 성공 확인

### DB 쿼리
```sql
-- 자막 있는 레코드 확인
SELECT COUNT(*) 
FROM video_captions 
WHERE segments_json->'tracks' != '[]'::jsonb;

-- 자막 샘플 확인
SELECT 
    id,
    competitor_video_id,
    segments_json->'source' as source,
    jsonb_array_length(segments_json->'tracks') as track_count
FROM video_captions 
LIMIT 10;
```

---

## 🎯 다음 단계

1. **Cookies 추출** (5분)
2. **환경 변수 설정** (1분)
3. **테스트 실행** (1분)
4. **성공 시 대량 재처리** (시간에 따라)

설정 완료 후 자막이 정상적으로 저장됩니다!
