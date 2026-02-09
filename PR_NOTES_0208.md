# PR: 뉴스 검색 키워드 전달 버그 수정 + DB 저장 파이프라인 + GPT 필터 개선

**Date**: 2026-02-08  
**Branch**: feature/async-refactor  
**Files Changed**: 16 (12 modified + 4 new)

---

## 🐛 1. 뉴스 검색 키워드 미전달 버그 수정

### 문제
- AI 추천 주제로 스크립트 생성 시 `topic_recommendation_id`가 BE로 전달되지 않음
- Recommender가 생성한 `search_keywords`를 못 불러와서 뉴스 검색이 빈 쿼리로 실행
- → 무관한 기사만 수집됨

### 원인
- FE에서 스크립트 페이지로 이동할 때 `topicId`를 URL 파라미터에 포함하지 않음

### 수정
| 파일 | 변경 |
|:---|:---|
| `FE/src/pages/script/page.tsx` | URL에서 `topicId` 파싱 → `executeScriptGen`에 전달 |
| `FE/src/lib/api/services/script-gen.service.ts` | `topic_recommendation_id` 파라미터 추가, API 요청에 포함 |
| `BE/app/schemas/script_gen.py` | `TopicContextResponse`에 `search_keywords` 필드 추가 |
| `BE/src/script_gen/utils/input_builder.py` | `_build_topic_context`에 `search_keywords`, `based_on_topic` 추가 |

---

## 🗂️ 2. 파이프라인 결과 DB 저장

### 목적
- 스크립트 생성 결과를 DB에 영구 저장 (새로고침해도 결과 유지)
- 이력 조회 API 제공

### 신규 파일 (4개)

| 파일 | 내용 |
|:---|:---|
| `BE/app/models/topic_request.py` | **TopicRequest** (파이프라인 중심 허브), **AgentRun** (에이전트 실행 이력) |
| `BE/app/models/script_pipeline.py` | **ContentBrief, ArticleSet, Article, ArticleAsset, FactSet, Fact, FactEvidence, FactDedupeCluster, VisualPlan, InsightSentence, InsightPack** |
| `BE/app/models/script_output.py` | **ScriptDraft, ScriptClaim, ScriptSourceMap, VerifiedScript** |
| `BE/alembic/versions/2026_02_08_1356-*.py` | Alembic 마이그레이션 (위 테이블 전부 생성) |

### 수정 파일

| 파일 | 변경 |
|:---|:---|
| `BE/app/models/__init__.py` | 신규 모델 17개 import + `__all__` 등록 |
| `BE/app/worker.py` | ① `_create_topic_request()` 자동 생성 ② `_save_result_to_db()` ScriptDraft + VerifiedScript 저장 ③ `user_id`, `channel_id` 파라미터 추가 |
| `BE/app/api/routes/script_gen.py` | ① `topic_context`를 `channel_profile`에 병합 ② `user_id/channel_id` 전달 ③ **GET `/scripts/history`** 이력 조회 API ④ **GET `/scripts/{id}`** 개별 조회 API |

### DB 테이블 구조
```
topic_requests (중심 허브)
├── agent_runs (에이전트 실행 이력)
├── content_briefs (Planner 결과)
├── article_sets → articles → article_assets (뉴스 수집)
├── fact_sets → facts → fact_evidences (팩트 추출)
│            → fact_dedupe_clusters (중복 제거)
│            → visual_plans (시각 자료 제안)
│            → insight_sentences (인사이트)
├── insight_packs (Insight Builder 결과)
├── script_drafts → script_claims → script_source_maps (Writer)
└── verified_scripts (Verifier 최종 결과)
```

---

## 🔧 3. GPT 뉴스 필터 프롬프트 개선

### 문제
- Recommender 키워드가 정상 전달되어도 "한의학 학술대회", "개발자 커리어 특강" 같은 무관한 기사가 포함됨
- 원인: 기사 설명에 "ChatGPT", "Claude"가 잠깐 언급만 돼도 관련 기사로 판정

### 수정 (Chain-of-Thought 방식)

**이전**: "관련 있는 기사 골라" (단순 판단)

**수정 후**: 2단계 사고 강제
1. **Step 1**: GPT가 주제에서 핵심 대상(고유명사) 추출
   - 예: "챗GPT와 클로드 비교 분석" → `챗GPT, ChatGPT, 클로드, Claude, OpenAI, Anthropic`
   - "AI", "기술" 같은 범용어는 제외
2. **Step 2**: 스크립트 작성자 관점으로 판단
   - 핵심 질문: "이 기사를 열면 스크립트에 직접 인용할 내용이 있는가?"
   - 다른 분야에서 핵심 대상을 잠깐 언급만 하는 기사는 제외
   - 제목에 핵심 대상이 없고 설명에만 있으면 의심

### 수정 파일

| 파일 | 변경 |
|:---|:---|
| `BE/src/script_gen/nodes/news_research.py` | GPT 필터 프롬프트 전면 개선 (Chain-of-Thought + 스크립트 관점 판단) |

### 테스트 결과 (주제: "챗GPT와 클로드 비교 분석")

| 구분 | 무관한 기사 | 관련 기사 |
|:---|:---|:---|
| **수정 전** | 한의신문, 베리타스알파(커리어특강) | 2/5 |
| **수정 후** | 없음 | **5/5 전부 관련** ✅ |

### 추가 비용
- **없음**. GPT 호출 횟수 동일 (1회), 프롬프트 텍스트만 변경

---

## 🛡️ 4. Fan-in Guard 추가

### 목적
- LangGraph 병렬 실행 시 선행 노드가 skip된 경우, 후속 노드에서 불필요한 GPT 호출 방지

### 수정 파일

| 파일 | 변경 |
|:---|:---|
| `BE/src/script_gen/nodes/insight_builder.py` | `competitor_data` 없으면 skip |
| `BE/src/script_gen/nodes/writer.py` | `insight_pack` 없으면 skip |
| `BE/src/script_gen/nodes/verifier.py` | `script_draft` 없으면 skip |

---

## 🎯 5. Planner 컨텍스트 강화

### 수정 파일

| 파일 | 변경 |
|:---|:---|
| `BE/src/script_gen/nodes/planner.py` | 프롬프트에 `based_on_topic`, `search_keywords`, `differentiator`, `title_patterns` 주입 |
| `BE/src/script_gen/utils/input_builder.py` | `_build_channel_profile`에 `differentiator`, `title_patterns` 추가 |

---

## 📊 전체 파일 목록

### 신규 (4개)
- `BE/app/models/topic_request.py`
- `BE/app/models/script_pipeline.py`
- `BE/app/models/script_output.py`
- `BE/alembic/versions/2026_02_08_1356-6a3cefa3f447_add_script_pipeline_tables.py`

### 수정 (12개)
- `BE/app/api/routes/script_gen.py` (+116 lines)
- `BE/app/models/__init__.py` (+35 lines)
- `BE/app/schemas/script_gen.py` (+1 line)
- `BE/app/worker.py` (+119/-14 lines)
- `BE/src/script_gen/nodes/insight_builder.py` (+5 lines)
- `BE/src/script_gen/nodes/news_research.py` (+136/-6 lines)
- `BE/src/script_gen/nodes/planner.py` (+18 lines)
- `BE/src/script_gen/nodes/verifier.py` (+5/-1 lines)
- `BE/src/script_gen/nodes/writer.py` (+5 lines)
- `BE/src/script_gen/utils/input_builder.py` (+8 lines)
- `FE/src/lib/api/services/script-gen.service.ts` (+24/-1 lines)
- `FE/src/pages/script/page.tsx` (+28/-1 lines)
