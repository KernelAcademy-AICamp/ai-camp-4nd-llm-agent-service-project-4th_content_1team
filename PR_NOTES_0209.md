# PR Notes - 2026.02.09

## 📌 주요 변경사항 요약

YouTube 검색 0건 반환 문제 해결 + 뉴스 관련도 필터 다축 인식 개선

---

## 1. YouTube Fetcher 검색 0건 문제 해결

### 문제
- `yt_fetcher_node`가 `content_brief.search_queries`에서 검색 쿼리를 가져오는데, **Planner가 이 키를 생성하지 않음**
- fallback으로 topic 제목 전체가 검색어로 사용됨
  - 예: `"AI, 어디까지 왔나? Claude 3 출시와 AI의 윤리적 문제 심층 분석"` → YouTube 결과 0건
- 반면 프론트엔드 CompetitorAnalysis 컴포넌트는 `search_keywords` (짧은 키워드)로 검색해서 정상 동작

### 원인
```
yt_fetcher가 기대하는 것:  content_brief.search_queries = ["Claude 3 성능 비교", ...]
Planner가 실제 반환한 것:  content_brief = {chapters: [...], ...}  ← search_queries 키 없음!
```

### 해결
**파일:** `BE/src/script_gen/nodes/planner.py` (100줄 부근)

Planner가 `content_brief` 반환 시, state의 `search_keywords`를 `search_queries`로 주입:

```python
# search_keywords → search_queries (yt_fetcher용)
topic_context = state.get("channel_profile", {}).get("topic_context", {})
search_keywords = topic_context.get("search_keywords", []) if topic_context else []
if search_keywords:
    content_brief["search_queries"] = search_keywords
```

### 데이터 흐름 (수정 후)
```
Recommender → search_keywords: ["Claude 3 성능 비교", "AI 윤리 문제점", ...]
                     ↓
Planner → content_brief.search_queries = search_keywords
                     ↓
yt_fetcher → search_queries로 YouTube API 검색 → 10개 영상 발견 ✅
```

### 결과
| 항목 | 수정 전 | 수정 후 |
|---|---|---|
| YouTube 검색 결과 | **0건** ❌ | **10건** ✅ |
| Competitor 분석 | skip | 5개 영상 분석 완료 |

---

## 2. GPT 뉴스 관련도 필터 — 다축 주제 인식 개선

### 문제
- GPT 필터가 **고유명사(1축)만** 핵심 대상으로 추출
- 복합 주제 `"Claude 3 출시 + AI 윤리"` → `Claude, Anthropic`만 잡고 "AI 윤리" 관련 기사 전부 탈락

```
수정 전 핵심대상: Claude 3, Claude, Anthropic (고유명사만)
→ 73개 후보 중 8개만 통과
→ AI 윤리 관련 기사 전부 탈락 ❌
```

### 해결
**파일:** `BE/src/script_gen/nodes/news_research.py` (`_filter_relevant_articles` 함수)

Step 1을 **2개 그룹**으로 분리:

```
Step 1. 핵심 키워드 그룹 추출 (2개 그룹)

그룹A - 고유명사: 제품명, 인물명, 기업명 (예: Claude, Anthropic)
그룹B - 핵심 개념: 주제의 구체적 테마 (예: AI 윤리, AI 편향성)

Step 2. 기사별 판단
→ 그룹A OR 그룹B에 해당하면 포함
```

### 프롬프트 변경 핵심
| 항목 | 수정 전 | 수정 후 |
|---|---|---|
| 핵심 대상 추출 | 고유명사만 | **그룹A(고유명사) + 그룹B(핵심개념)** |
| 포함 기준 | 고유명사에 해당하는 기사만 | **그룹A OR 그룹B** 해당하면 포함 |
| 응답 형식 | `핵심대상: ...` | `그룹A: ...` / `그룹B: ...` |

### 결과
```
수정 후:
그룹A(고유명사): Claude 3, Claude, Anthropic, 오픈AI, GPT, 제미나이
그룹B(핵심개념): AI 윤리, AI 편향성, 책임 AI, AI 규제
→ 73개 후보 중 10개 통과 (+2개 추가 확보)
```

| 항목 | 수정 전 | 수정 후 |
|---|---|---|
| 핵심 대상 | 3개 (Claude 계열만) | **그룹A: 6개 + 그룹B: 4개** |
| 필터 통과 기사 | 8개 | **10개 (+25%)** |
| 팩트 인용 | 5개 | **6개** |
| Verifier 통과율 | 37% | **50%** |

---

## 📁 변경 파일 목록

### 수정된 파일
| 파일 | 변경 내용 |
|---|---|
| `BE/src/script_gen/nodes/planner.py` | `content_brief`에 `search_queries` 추가 |
| `BE/src/script_gen/nodes/news_research.py` | GPT 필터 프롬프트 다축 인식 + 파싱 로직 변경 |

### 영향 범위
- `yt_fetcher.py`: 변경 없음 (기존에 `search_queries` 읽는 코드 이미 있음)
- `state.py`: 변경 없음 (`Dict[str, Any]`이라 키 추가 자유)
- `graph.py`: 변경 없음 (노드 연결 변경 없음)

---

## 🔜 TODO (미해결)

### 높은 우선순위
- [ ] **Insight Builder 논지가 너무 뻔함** — "AI 발전은 윤리와 함께해야" 수준
  - 원래 목적: "경쟁이 놓친 포인트를 찾아 차별화된 논지 도출"
  - 프롬프트 튜닝 필요 (금지 패턴 추가, 구체적 사실 기반 논지 유도)

### 중간 우선순위
- [ ] Fan-in Guard skip 로그 레벨 정리 (INFO → DEBUG)
- [ ] 뉴스 이미지 수집 불안정 (5개 중 1~2개만 이미지 확보)
- [ ] Verifier 통과율 개선 (현재 50%, 실패 원인 분석 필요)
