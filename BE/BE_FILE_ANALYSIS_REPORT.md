# BE 폴더 전체 파일 기능 분석 보고서

## 📁 src/script_gen/nodes (AI 에이전트 노드들)

### ✅ 구현 완료 (코드 있음)
| 파일명 | 크기 | 기능 |
|:---|---:|:---|
| `planner.py` | 19,562 bytes | 주제 분석 → 목차/질문/검색어 생성 |
| `news_research.py` | 31,535 bytes | 뉴스 수집 + Fact Extraction (통합) |
| `trend_scout.py` | 16,414 bytes | 레딧 트렌드 키워드 수집 |
| `insight_builder.py` | 9,027 bytes | 전략 수립 (2-Pass: Draft → Critic) |
| `writer.py` | 5,575 bytes | 대본 작성 (Phase 1 MVP) |

### ❌ 미구현 (0 Byte)
| 파일명 | 상태 | 원래 역할 |
|:---|:---:|:---|
| `yt_fetcher.py` | **0 Byte** | 유튜브 인기 영상 검색 |
| `competitor_anal.py` | **0 Byte** | 경쟁 영상 분석 (훅/구조/약점) |
| `fact_extractor.py` | **0 Byte** | (이미 news_research.py에 통합됨) |
| `metadata_gen.py` | **0 Byte** | 메타데이터 생성 (미정의) |
| `verifier.py` | **0 Byte** | 팩트 체크 및 검증 |

---

## 📁 app/services (백엔드 서비스 - API 로직)

### ✅ 완전 구현
| 파일명 | 기능 |
|:---|:---|
| `youtube_service.py` | 유튜브 API 연동 (인기 영상 검색, 채널 통계) |
| `competitor_service.py` | 경쟁사 영상 저장, 댓글 수집 (좋아요순 정렬) |
| `subtitle_service.py` | 자막 추출 (Innertube + 라이브러리 이중화) |
| `auth_service.py` | 구글 OAuth, JWT 세션 관리 |

---

## 📁 app/api/routes (FastAPI 엔드포인트)

| 파일명 | 제공 API |
|:---|:---|
| `youtube.py` | `/youtube/search`, `/youtube/channel-sync` |
| `competitor.py` | `/competitor/save`, `/competitor/comments` |
| `subtitle.py` | `/subtitle/fetch` |
| `auth.py` | `/auth/google/login`, `/auth/refresh` |

---

## 📁 app/models (DB 스키마)

| 파일명 | 테이블 |
|:---|:---|
| `youtube_channel.py` | `youtube_channels`, `yt_channel_stats_daily` |
| `competitor.py` | `competitor_collections`, `competitor_videos`, `video_comment_samples` |
| `caption.py` | `video_captions` |
| `thumbnail_generation.py` | `thumbnail_generations` |

---

## 🔍 결론: 유튜브 기능은 어디에?

**발견 사항:**
1. **유튜브 검색/분석 기능**은 `app/services/youtube_service.py`에 **완벽히 구현**되어 있습니다.
2. **경쟁사 분석 기능**도 `app/services/competitor_service.py`에 **완벽히 구현**되어 있습니다.
3. 하지만 **AI 에이전트 노드**(`src/script_gen/nodes/`)에서 이 서비스를 **호출하는 코드가 없습니다**.

**즉:**
- **재료(Service)** ✅ 있음
- **요리사(Agent Node)** ❌ 없음 (0 Byte 파일)

**해결 방법:**
`yt_fetcher.py`와 `competitor_anal.py`에 **서비스 호출 코드 5~10줄**만 추가하면 바로 작동합니다.

지금 바로 이 두 파일을 구현할까요?
