# 프로젝트 코드 분석 보고서

## 1. 요약: "빈 main.py" 이슈에 대하여
`BE/src/main.py` 파일이 비어있는 것은 **오류가 아닐 가능성이 매우 높습니다.** 프로젝트 구조를 살펴본 결과, 실제 애플리케이션의 진입점(Entry Point)은 **`BE/app/main.py`** 로 이동되었거나 그곳에 위치하고 있습니다.

- **현재 진입점**: `BE/app/main.py` (FastAPI 애플리케이션)
- **레거시/미사용**: `BE/src/main.py` (무시하거나 삭제해도 안전함)

이 애플리케이션은 **FastAPI** 서버로 실행되도록 설계되었으며, 일반적으로 다음 명령어로 실행됩니다:
`uvicorn app.main:app --reload`

## 2. 프로젝트 구조 개요
백엔드(`BE`)는 크게 두 가지 영역으로 나뉩니다:
1. **`app/`**: 웹 서버 (FastAPI). API 요청을 처리하고, 데이터베이스와 연동하며, 프론트엔드에 데이터를 제공합니다.
2. **`src/`**: AI 로직 (에이전트). 플랫폼의 핵심 "두뇌" 역할을 합니다 (주제 추천, 대본 작성 등).

### 디렉토리 구조 상세
```
BE/
├── app/                  # [웹 애플리케이션 레이어]
│   ├── main.py           # <--- 실제 진입점 (FastAPI 앱)
│   ├── api/              # API 라우트 (엔드포인트)
│   ├── services/         # 비즈니스 로직 (YouTube API, 인증 등)
│   ├── models/           # 데이터베이스 모델
│   └── core/             # 설정 및 DB 초기화
│
├── src/                  # [AI 에이전트 레이어]
│   ├── topic_rec/        # 주제 추천 엔진 (LangGraph)
│   ├── script_gen/       # 대본 생성 에이전트
│   └── thumbnail/        # 썸네일 생성 에이전트
│
├── docker-compose.yml    # 데이터베이스 (Postgres) 및 도구 설정
└── requirements.txt      # Python 의존성 목록
```

## 3. 주요 파일 상세 분석

### A. 애플리케이션 레이어 (`app/`)
HTTP 요청과 표준 백엔드 기능을 처리하는 레이어입니다.

| 파일 / 디렉토리 | 용도 |
|------------------|---------|
| **`app/main.py`** | **앱의 핵심.** FastAPI 초기화, CORS 설정, 라우터 포함 등을 담당합니다. |
| `app/api/routes/` | 엔드포인트 정의. <br> - `youtube.py`: YouTube 검색 및 데이터 가져오기 API. <br> - `auth.py`: 사용자 인증. |
| `app/services/` | API에서 사용하는 공통 로직. <br> - `youtube_service.py`: 복잡한 YouTube API 연동 로직 처리. |

### B. AI 에이전트 레이어 (`src/`)
지능형 에이전트들이 포함된 레이어입니다. 일부는 구현이 완료되었으나, 일부(조정/Orchestration)는 작업 중(WIP)인 것으로 보입니다.

| 모듈 | 상태 | 설명 |
|--------|--------|-------------|
| **`topic_rec/`** | **활성 (Active)** | 주제 추천 엔진. <br> - `graph.py`: LangGraph 워크플로우 정의 (`수집` -> `처리` -> `추천`). <br> - `nodes/`: 각 단계별 로직 포함. |
| **`script_gen/`** | **부분 구현** | 대본 생성 로직. <br> - **`graph.py` 비어있음**: 전체 흐름을 제어하는 로직이 누락되었거나 아직 커밋되지 않았습니다. <br> - `nodes/trend_scout.py`: **구현 완료**. Reddit 트렌드 수집 및 LLM 키워드 추출. <br> - `nodes/news_research.py`: **구현됨**. 뉴스 리서치를 담당하는 대형 로직. |
| **`thumbnail/`** | **부분 구현** | 썸네일 생성. <br> - **`graph.py` 비어있음**: 오케스트레이션 로직 누락. |

## 4. 실행 가이드
현재 파일 구조를 기반으로 애플리케이션을 실행하는 방법입니다:

1. **데이터베이스 시작**:
   ```bash
   docker-compose up -d
   ```

2. **백엔드 서버 실행**:
   (`BE/` 디렉토리 내에서)
   ```bash
   # PYTHONPATH 설정이 필요할 수 있습니다
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   
   # 서버 실행 (Windows PowerShell 예시)
   # $env:PYTHONPATH += ";$(Get-Location)"
   uvicorn app.main:app --reload
   ```

3. **AI 에이전트 독립 실행** (선택 사항):
   Topic Recommendation(주제 추천) 엔진을 CLI에서 직접 테스트할 수 있습니다:
   ```bash
   python -m src.topic_rec.graph tech_kr
   ```
