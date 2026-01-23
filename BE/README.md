# YouTube Maker Backend

FastAPI 백엔드 서버 with Google OAuth 인증

## 기술 스택

- **FastAPI** - 웹 프레임워크
- **SQLAlchemy 2.0** - ORM (async)
- **Alembic** - 데이터베이스 마이그레이션
- **PostgreSQL** - 데이터베이스
- **JWT** - 토큰 기반 인증
- **Google OAuth 2.0** - 소셜 로그인

## 프로젝트 구조

```
BE/
├── app/
│   ├── api/
│   │   └── routes/
│   │       └── auth.py          # 인증 API 엔드포인트
│   ├── core/
│   │   ├── config.py            # 설정 관리
│   │   ├── db.py                # 데이터베이스 연결
│   │   └── security.py          # JWT 및 보안 유틸리티
│   ├── models/
│   │   ├── user.py              # User 모델
│   │   ├── oauth.py             # OAuth 계정 모델
│   │   ├── session.py           # 세션 모델
│   │   └── jwt_token.py         # JWT 리프레시 토큰 모델
│   ├── schemas/
│   │   └── auth.py              # Pydantic 스키마
│   ├── services/
│   │   ├── google_oauth.py      # Google OAuth 서비스
│   │   └── auth_service.py      # 인증 비즈니스 로직
│   └── main.py                  # FastAPI 애플리케이션
├── alembic/
│   ├── versions/                # 마이그레이션 파일
│   ├── env.py                   # Alembic 환경 설정
│   └── script.py.mako           # 마이그레이션 템플릿
├── docker-compose.yml           # PostgreSQL 컨테이너
├── alembic.ini                  # Alembic 설정
├── requirements.txt             # Python 의존성
└── .env.example                 # 환경 변수 예시
```

## 설치 및 실행

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 다음 값들을 설정하세요:
- `GOOGLE_CLIENT_ID`: Google Cloud Console에서 발급받은 클라이언트 ID
- `GOOGLE_CLIENT_SECRET`: Google Cloud Console에서 발급받은 클라이언트 시크릿
- `JWT_SECRET`: JWT 서명용 시크릿 키 (랜덤 문자열)

### 2. PostgreSQL 시작

```bash
docker-compose up -d
```

이 명령으로 두 개의 컨테이너가 실행됩니다:
- **PostgreSQL**: 데이터베이스 서버 (포트 5433)
- **Adminer**: 웹 기반 DB 관리 도구 (포트 8081)

#### 웹에서 데이터베이스 보기 (Adminer)

브라우저에서 http://localhost:8081 접속 후 다음 정보로 로그인:

| 항목 | 값 |
|------|-----|
| **System** | PostgreSQL |
| **Server** | postgres |
| **Username** | postgres |
| **Password** | postgres |
| **Database** | youtube_maker_db |

로그인 후:
1. 좌측 메뉴에서 테이블 선택 (예: `user`, `oauth_account`, `session`)
2. 테이블 데이터를 직접 조회/수정/삭제 가능
3. SQL 쿼리 직접 실행 가능

### 3. Python 가상환경 생성 및 의존성 설치

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 데이터베이스 마이그레이션

```bash
# 마이그레이션 파일 생성
alembic revision --autogenerate -m "Initial migration"

# 마이그레이션 실행
alembic upgrade head
```

### 5. 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

서버가 `http://localhost:8000`에서 실행됩니다.

## API 엔드포인트

### 인증

#### `POST /auth/google/callback`
Google OAuth 인증 코드를 받아 로그인 처리

**Request:**
```json
{
  "code": "google_authorization_code",
  "redirectUri": "http://localhost:5173"
}
```

**Response:**
```json
{
  "user": {
    "userId": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "avatarUrl": "https://..."
  },
  "tokens": {
    "accessToken": "jwt_access_token",
    "refreshToken": "jwt_refresh_token",
    "tokenType": "bearer",
    "expiresInSec": 900
  }
}
```

#### `GET /auth/me`
현재 로그인한 사용자 정보 조회

**Headers:**
- `Authorization: Bearer {access_token}` (선택)
- `Cookie: session_token={session_token}` (선택)

**Response:**
```json
{
  "userId": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "avatarUrl": "https://..."
}
```

#### `POST /auth/refresh`
Access Token 갱신

**Request:**
```json
{
  "refreshToken": "jwt_refresh_token"
}
```

**Response:**
```json
{
  "accessToken": "new_jwt_access_token",
  "expiresInSec": 900
}
```

#### `POST /auth/logout`
로그아웃 (세션 폐기)

**Response:**
```json
{
  "ok": true
}
```

## 인증 방식

이 백엔드는 **이중 인증 전략**을 지원합니다:

1. **세션 쿠키 (기본)**: HttpOnly 쿠키를 통한 서버 세션 방식
2. **JWT 토큰 (선택)**: Authorization 헤더를 통한 토큰 방식

프론트엔드는 둘 중 하나를 선택하여 사용할 수 있습니다.

## 테스트

### curl을 사용한 테스트

```bash
# 1. Google OAuth 로그인 (실제 authorization code 필요)
curl -X POST http://localhost:8000/auth/google/callback \
  -H "Content-Type: application/json" \
  -d '{"code": "your_google_auth_code", "redirectUri": "http://localhost:5173"}'

# 2. 현재 사용자 조회 (JWT 사용)
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 3. 현재 사용자 조회 (세션 쿠키 사용)
curl -X GET http://localhost:8000/auth/me \
  -H "Cookie: session_token=YOUR_SESSION_TOKEN"

# 4. 토큰 갱신
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refreshToken": "YOUR_REFRESH_TOKEN"}'

# 5. 로그아웃
curl -X POST http://localhost:8000/auth/logout \
  -H "Cookie: session_token=YOUR_SESSION_TOKEN"
```

## 보안 고려사항

### 현재 구현 (MVP)
- ✅ HttpOnly 쿠키
- ✅ CORS 설정
- ✅ JWT 토큰 검증
- ✅ 세션 만료 처리
- ✅ 토큰 폐기 기능

### TODO (프로덕션 배포 전)
- ⚠️ OAuth 토큰 암호화 (현재 평문 저장)
- ⚠️ 세션 토큰 해싱
- ⚠️ CSRF 토큰 추가
- ⚠️ Rate limiting
- ⚠️ HTTPS 강제 (Secure 쿠키)

## 데이터베이스 스키마

### users
- `id`: UUID (PK)
- `email`: String (Unique)
- `name`: String (Nullable)
- `avatar_url`: String (Nullable)
- `google_sub`: String (Unique, Nullable)
- `created_at`, `updated_at`: DateTime

### oauth_accounts
- `id`: UUID (PK)
- `user_id`: UUID (FK → users)
- `provider`: String (default: 'google')
- `provider_account_id`: String (Google sub)
- `access_token`, `refresh_token`: String (Nullable)
- `scope`: String (Nullable)
- `expires_at`: Integer (Unix timestamp)
- `created_at`, `updated_at`: DateTime

### sessions
- `id`: UUID (PK)
- `user_id`: UUID (FK → users)
- `session_token`: String (Unique)
- `created_at`, `expires_at`: DateTime
- `revoked_at`: DateTime (Nullable)
- `user_agent`, `ip`: String (Nullable)

### jwt_refresh_tokens
- `id`: UUID (PK)
- `user_id`: UUID (FK → users)
- `jti`: String (Unique, JWT ID)
- `issued_at`, `expires_at`: DateTime
- `revoked_at`: DateTime (Nullable)
- `replaced_by_jti`: String (Nullable)

## 라이선스

MIT
