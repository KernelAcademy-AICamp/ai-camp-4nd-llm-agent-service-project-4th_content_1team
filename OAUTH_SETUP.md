# Google OAuth 설정 가이드

## 1. Google Cloud Console 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. "API 및 서비스" > "사용자 인증 정보" 메뉴로 이동
4. "사용자 인증 정보 만들기" > "OAuth 클라이언트 ID" 선택
5. 애플리케이션 유형: "웹 애플리케이션" 선택
6. 승인된 리디렉션 URI 추가:
   - `http://localhost:5173`
   - `http://localhost:5173/` (슬래시 포함)
7. 클라이언트 ID와 클라이언트 보안 비밀번호 복사

## 2. 환경 변수 설정

### 프론트엔드 (FE/.env.local)
```env
VITE_GOOGLE_CLIENT_ID=your_google_client_id_here
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_REDIRECT_URI=http://localhost:5173
```

### 백엔드 (BE/.env)
```env
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:5173
```

## 3. 데이터베이스 설정

```bash
cd BE

# PostgreSQL 시작
docker-compose up -d

# 마이그레이션 생성 및 적용
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## 4. 서버 실행

### 백엔드
```bash
cd BE
uvicorn app.main:app --reload
```

### 프론트엔드
```bash
cd FE
npm run dev
```

## 5. 테스트

1. http://localhost:5173 접속
2. "Google 계정으로 계속하기" 버튼 클릭
3. Google 로그인 페이지로 리디렉션
4. 로그인 후 애플리케이션으로 돌아옴
5. 온보딩 페이지로 자동 이동

## 문제 해결

### CORS 오류
- 백엔드 `.env`의 `CORS_ORIGINS`에 프론트엔드 URL 추가 확인

### 리디렉션 오류
- Google Cloud Console의 승인된 리디렉션 URI 확인
- 프론트엔드와 백엔드의 `GOOGLE_REDIRECT_URI` 일치 확인

### 데이터베이스 연결 오류
- PostgreSQL 컨테이너 실행 확인: `docker ps`
- 포트 5432가 사용 가능한지 확인
