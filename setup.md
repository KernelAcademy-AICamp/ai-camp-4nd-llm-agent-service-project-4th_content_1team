# YouTube Maker 프로젝트 설정 가이드

이 문서는 프로젝트를 처음 세팅하는 분들을 위한 단계별 가이드입니다.

---

## 1. 사전 준비물

아래 프로그램들을 먼저 설치해주세요.

| 프로그램 | 최소 버전 | 다운로드 링크 |
|---------|----------|-------------|
| Git | 최신 | https://git-scm.com/downloads |
| Node.js | v18 이상 | https://nodejs.org/ (LTS 버전 권장) |
| Python | 3.11 이상 | https://www.python.org/downloads/ |
| Docker Desktop | 최신 | https://www.docker.com/products/docker-desktop/ |

> **Python 설치 시 주의**: 설치 화면에서 **"Add Python to PATH"** 체크박스를 반드시 체크하세요.

설치 확인 (터미널에서 실행):

```bash
git --version
node --version
python --version
docker --version
```

모두 버전 번호가 출력되면 준비 완료입니다.

---

## 2. 프로젝트 다운로드

```bash
git clone https://github.com/KernelAcademy-AICamp/ai-camp-4nd-llm-agent-service-project-4th_content_1team.git
cd ai-camp-4nd-llm-agent-service-project-4th_content_1team
```

---

## 3. 데이터베이스 실행 (Docker)

Docker Desktop이 실행 중인지 확인한 후 아래 명령어를 입력합니다.

```bash
cd BE
docker-compose up -d
```

이 명령어는 다음 두 개의 컨테이너를 실행합니다:
- **PostgreSQL** (포트 `5433`) — 데이터베이스
- **Adminer** (포트 `8081`) — DB 관리 웹 도구

정상 실행 확인:

```bash
docker ps
```

`youtube_maker_db`와 `youtube_maker_adminer` 두 컨테이너가 보이면 성공입니다.

---

## 4. 백엔드 설정 및 실행

### 4-1. 가상환경 생성 및 활성화

```bash
# BE 폴더에서 실행 (이미 BE 폴더에 있다면 생략)
cd BE

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

> 터미널 앞에 `(venv)`가 표시되면 활성화된 상태입니다.

### 4-2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4-3. 환경변수 설정

```bash
# Windows:
copy .env.example .env
# Mac/Linux:
cp .env.example .env
```

`.env` 파일을 열어서 아래 항목을 실제 값으로 수정합니다:

```
GOOGLE_CLIENT_ID=발급받은_클라이언트_ID
GOOGLE_CLIENT_SECRET=발급받은_클라이언트_시크릿
YOUTUBE_API_KEY=발급받은_유튜브_API_키
```

> API 키 발급 방법은 [6. API 키 발급 가이드](#6-api-키-발급-가이드)를 참고하세요.

**중요**: `DATABASE_URL`의 포트가 `5433`인지 확인하세요. Docker에서 호스트 포트를 5433으로 매핑합니다.

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/youtube_maker_db
```

> `.env.example`의 기본값은 포트 `5432`로 되어 있으므로 **반드시 `5433`으로 변경**해주세요.

* 잘 모르겠으면 개발자에게 문의하세요

### 4-4. DB 마이그레이션

```bash
alembic upgrade head
```

### 4-5. 서버 실행

```bash
uvicorn app.main:app --reload
```

백엔드가 `http://localhost:8000`에서 실행됩니다.

---

## 5. 프론트엔드 설정 및 실행

새 터미널을 열고 진행합니다.

```bash
cd FE

npm install
```

환경변수 파일 복사:

```bash
# Windows:
copy .env.example .env
# Mac/Linux:
cp .env.example .env
```

`.env` 파일을 열어서 Google Client ID를 입력합니다:

```
VITE_GOOGLE_CLIENT_ID=발급받은_클라이언트_ID
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_REDIRECT_URI=http://localhost:5173
```

* env 정보를 개발자에게 문의해서 받으세요 

개발 서버 실행:

```bash
npm run dev
```

프론트엔드가 `http://localhost:5173`에서 실행됩니다.

---

## 6. API 키 발급 가이드

### Google OAuth 클라이언트 ID / Secret

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 (또는 기존 프로젝트 선택)
3. **API 및 서비스 > 사용자 인증 정보** 이동
4. **사용자 인증 정보 만들기 > OAuth 클라이언트 ID** 클릭
5. 애플리케이션 유형: **웹 애플리케이션** 선택
6. **승인된 리디렉션 URI**에 `http://localhost:5173` 추가
7. 생성 후 **클라이언트 ID**와 **클라이언트 보안 비밀번호**를 복사

> 처음 만드는 경우 **OAuth 동의 화면** 설정이 먼저 필요합니다. 테스트 단계에서는 "외부" 유형으로 생성하고, 테스트 사용자에 본인 이메일을 추가하세요.

### YouTube Data API 키

1. [Google Cloud Console](https://console.cloud.google.com/)에서 같은 프로젝트 선택
2. **API 및 서비스 > 라이브러리** 이동
3. "YouTube Data API v3" 검색 후 **사용** 클릭
4. **API 및 서비스 > 사용자 인증 정보** 이동
5. **사용자 인증 정보 만들기 > API 키** 클릭
6. 생성된 API 키를 복사

---

## 7. 실행 확인

모든 설정이 완료되면 아래 주소에 접속해보세요.

| 서비스 | URL | 설명 |
|-------|-----|------|
| 프론트엔드 | http://localhost:5173 | 메인 웹 페이지 |
| 백엔드 API | http://localhost:8000 | API 서버 |
| API 문서 | http://localhost:8000/docs | Swagger UI (API 테스트 가능) |
| DB 관리 | http://localhost:8081 | Adminer (DB 조회/수정) |

Adminer 로그인 정보:
- 시스템: PostgreSQL
- 서버: `postgres` (Docker 내부) 또는 `localhost:5433` (외부 접속)
- 사용자: `postgres`
- 비밀번호: `postgres`
- 데이터베이스: `youtube_maker_db`

---

## 8. 자주 발생하는 문제 (FAQ)

### Q: `docker-compose up -d` 실행 시 에러가 발생해요

- Docker Desktop이 실행 중인지 확인하세요.
- 포트 5433이 이미 사용 중일 수 있습니다. `docker ps`로 기존 컨테이너를 확인하세요.

### Q: `pip install` 시 에러가 발생해요

- 가상환경이 활성화되어 있는지 확인하세요 (터미널에 `(venv)` 표시).
- Python 버전이 3.11 이상인지 확인하세요: `python --version`

### Q: `alembic upgrade head` 시 DB 연결 에러가 발생해요

- Docker PostgreSQL이 실행 중인지 확인: `docker ps`
- `.env` 파일의 `DATABASE_URL` 포트가 `5433`인지 확인하세요.

### Q: 프론트엔드에서 로그인이 안 돼요

- `.env`의 `VITE_GOOGLE_CLIENT_ID`가 올바른지 확인하세요.
- Google Cloud Console에서 리디렉션 URI에 `http://localhost:5173`이 등록되어 있는지 확인하세요.
- 백엔드 `.env`의 `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`이 동일한 OAuth 앱의 값인지 확인하세요.

### Q: `npm run dev` 실행 시 에러가 발생해요

- Node.js 버전 확인: `node --version` (v18 이상)
- `node_modules` 삭제 후 재설치: `rm -rf node_modules && npm install`
- Windows의 경우: `rmdir /s /q node_modules` 후 `npm install`

### Q: 백엔드 서버는 실행되는데 API 호출이 안 돼요

- 프론트엔드 `.env`의 `VITE_API_URL`이 `http://localhost:8000`인지 확인하세요.
- 브라우저 개발자 도구(F12) > Network 탭에서 에러 내용을 확인하세요.
