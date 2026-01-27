## YouTube Maker Backend 시작 가이드 (venv 기반)

> 이 문서는 **로컬 개발 환경에서 백엔드(FastAPI) 서버를 실행**하기 위한 최소한의 절차를 정리한 가이드입니다.  
> 모든 명령은 `BE/` 디렉토리를 기준으로 실행합니다.

---

## 1. 사전 준비물

- **Python**: 3.10 이상 권장
- **Git**
- **Docker & Docker Compose**: PostgreSQL 컨테이너 실행용
- 터미널(Zsh, Bash, PowerShell 등)

백엔드 코드 루트는 다음과 같습니다.

```bash
cd /Users/fastcampus/Desktop/content-team/BE
```

---

## 2. 레포 클론 & 디렉토리 이동

이미 레포를 클론해두었다면 이 단계는 건너뛰어도 됩니다.

```bash
# 예시: GitHub에서 클론
git clone <YOUR_REPO_URL> content-team

cd content-team/BE
```

---

## 3. 가상환경(venv) 생성 & 활성화

### 3-1. venv 생성

```bash
python -m venv venv
```

프로젝트 루트(`BE/`) 아래에 `venv/` 폴더가 생성됩니다.

### 3-2. venv 활성화

- **macOS / Linux (Bash, Zsh)**:

```bash
source venv/bin/activate
```

- **Windows (PowerShell / CMD)**:

```bash
venv\Scripts\activate
```

터미널 프롬프트 앞에 `(venv)` 처럼 표시되면 가상환경이 정상적으로 활성화된 것입니다.

### 3-3. venv 비활성화

작업을 마치고 가상환경을 끄고 싶을 때:

```bash
deactivate
```

---

## 4. Python 의존성 설치

가상환경이 **활성화된 상태**에서 아래 명령을 실행합니다.

```bash
pip install -r requirements.txt
```

설치 중 `pip` 관련 경고가 뜰 경우, 필요하다면 다음과 같이 업데이트 후 다시 시도할 수 있습니다.

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. 환경 변수(.env) 설정

### 5-1. 예시 파일 복사

먼저 기본 템플릿에서 `.env` 파일을 생성합니다.

```bash
cp .env.example .env
```

### 5-2. 필수 항목 채우기

`BE/.env` 파일을 열어 아래 항목들을 실제 값으로 설정합니다.

- **Database**
  - `DATABASE_URL`
- **Google OAuth**
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `GOOGLE_REDIRECT_URI`
- **JWT 설정**
  - `JWT_SECRET`
- **YouTube Data API (인기 영상/기능 사용 시 필수)**
  - `YOUTUBE_API_KEY`

각 항목의 예시 값과 기본 구조는 이미 존재하는 다음 파일들을 참고하면 됩니다.

- `BE/.env.example`
- `BE/README.md` 의 “환경 변수 설정” 섹션

---

## 6. 데이터베이스(Docker) 실행

PostgreSQL과 Adminer는 `docker-compose.yml`로 한 번에 실행할 수 있습니다.

```bash
docker-compose up -d
```

이 명령을 실행하면:

- **PostgreSQL**: 기본 포트에서 DB 서버 실행
- **Adminer**: 웹 기반 DB 관리 도구 실행

Adminer 접속 및 로그인 정보는 `BE/README.md`를 참고하세요.

컨테이너를 중지하려면:

```bash
docker-compose down
```

---

## 7. 데이터베이스 마이그레이션(Alembic)

스키마가 이미 준비된 상태라면, 보통 아래 한 줄이면 충분합니다.

```bash
alembic upgrade head
```

### (참고) 스키마 변경 시 마이그레이션 파일 생성

모델을 수정하고 새로운 마이그레이션을 만들 때만 아래 명령을 사용합니다.

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

일반적으로 **처음 세팅하는 개발자**는 `alembic upgrade head`만 실행하면 됩니다.

---

## 8. 서버 실행 (uvicorn)

모든 준비(venv, 의존성, .env, DB, 마이그레이션)가 끝났다면 FastAPI 서버를 실행합니다.

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8-1. 동작 확인

- 기본 상태 확인:

```text
http://localhost:8000/
```

- API 문서(Swagger UI):

```text
http://localhost:8000/docs
```

---

## 9. 자주 쓰는 명령 요약 (Cheatsheet)

### venv 관련

```bash
# venv 생성
python -m venv venv

# macOS / Linux 활성화
source venv/bin/activate

# Windows 활성화
venv\Scripts\activate

# 비활성화
deactivate
```

### 서버 실행 / 종료

```bash
# FastAPI 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 터미널에서 서버 중지
Ctrl + C
```

### Docker (DB) 관련

```bash
# DB 및 Adminer 컨테이너 실행
docker-compose up -d

# 컨테이너 중지 및 정리
docker-compose down
```

---

이 문서만 순서대로 따라 하면, **로컬 머신에서 YouTube Maker 백엔드 서버를 venv 기반으로 실행**할 수 있습니다.

