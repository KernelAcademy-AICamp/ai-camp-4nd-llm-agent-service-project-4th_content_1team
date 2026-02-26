# 📋 2026-02-11 작업 일지: AI 스크립트 할루시네이션 & 인용 번호 매핑 수정

---

## 🎯 오늘의 목표

AI가 생성하는 유튜브 대본에서 두 가지 핵심 문제를 해결한다:

1. **할루시네이션(Hallucination)**: AI가 소스 기사에 없는 수치, 벤치마크 점수 등을 자체 학습 데이터에서 끌어와 스크립트에 날조
2. **인용 번호 매핑 오류**: 인용 번호(①②③...)가 실제 기사와 매칭되지 않는 문제

---

## 📌 문제 1: AI 스크립트 할루시네이션

### 증상

스크립트에 소스 기사에 **없는** 구체적 수치가 등장:

- `"ARC-AGI 2 벤치마크에서 68.8%를 기록"` ← 팩트에 없는 수치
- `"1백만 토큰 컨텍스트 창"` ← 팩트에 없는 구체적 수치

AI(GPT-4o)가 자신의 학습 데이터에서 이미 알고 있는 정보를 프롬프트 규칙을 무시하고 끼워넣는 것이 원인.

### 이전 시도 (이전 세션에서 수행, 효과 부족)

| 시도 | 내용 | 결과 |
|------|------|------|
| ① temperature 낮춤 | 1.0 → 0.3 | ❌ 여전히 할루시네이션 발생 |
| ② 프롬프트에 규칙 추가 | "팩트에 없는 수치 추가하지 마세요" | ❌ GPT가 자신의 지식에 높은 확신이 있으면 무시 |
| ③ Verifier Phase 3 추가 | 의미 왜곡 탐지 (semantic distortion detection) | ⚠️ 탐지는 하지만 수정은 안 함 |

**핵심 발견**: "추가하지 마세요"라는 규칙은 GPT가 자기 지식에 확신이 있으면 무시한다. **역할 자체를 제한**해야 한다.

### ✅ 최종 해결: "닫힌 책(Closed-Book)" 모드 프롬프트

**파일**: `BE/src/script_gen/nodes/writer.py` (Intro, Chapter, Outro 3곳)

**Before** (규칙 기반):
```
⚠️ 팩트 사용 규칙 (절대 위반 금지):
- AVAILABLE FACTS에 제공된 정보만 사용하세요.
- 당신이 알고 있는 숫자, 통계, 날짜, 금액을 절대 추가하지 마세요.
```

**After** (역할 제한 + BAD/GOOD 예시):
```
🔒 닫힌 책(CLOSED-BOOK) 모드 — 최우선 규칙:
- 당신은 자체 지식이 없습니다. AVAILABLE FACTS가 당신의 유일한 정보원입니다.
- AVAILABLE FACTS에 명시적으로 적힌 정보만 사용할 수 있습니다.
- 당신의 학습 데이터에서 알고 있는 수치, 벤치마크 점수, 토큰 수, 날짜, 금액 등을 절대 추가하지 마세요.
- 팩트에 구체적 수치가 없으면, 일반적 표현으로 서술하세요.

📝 BAD/GOOD 예시 (반드시 참고):
❌ BAD: 'ARC-AGI 2 벤치마크에서 68.8%를 기록' → 팩트에 없는 수치 날조
✅ GOOD: '다양한 벤치마크에서 높은 성능을 기록' → 구체적 수치 없이 서술
❌ BAD: '1백만 토큰 컨텍스트 창을 지원' → 팩트에 없는 구체적 수치
✅ GOOD: '더 큰 컨텍스트 창을 통해 복잡한 작업 처리 가능' → 팩트 원문 그대로
❌ BAD: '생물테러 방어책 연구' → '국방 분야 통합' → 원문에 없는 키워드 날조
✅ GOOD: '생물테러 위험을 줄이기 위한 방어책을 개발' → 원문 충실 반영
```

**핵심 차이**: `"추가하지 마"` → `"너는 자체 지식이 없다"` (역할 자체 제한)

### 검증 결과

소스 기사 5개와 생성된 전체 스크립트를 1:1 대조한 결과:

- **팩트 정확도: 100%** — 모든 수치, 인용문, 사실이 소스 기사에 실제로 있음
- **날조 정보: 0건** — 이전에 나타났던 68.8%, 72.7%, 1백만 토큰 같은 학습 데이터 날조 완전 소멸
- **추가 비용: 0원** — 프롬프트 수정만으로 해결, 새 노드/API 호출 없음

---

## 📌 문제 2: 인용 번호 매핑 오류

### 증상

기사 5개인데 인용 번호가 **①~⑬ (13개)** 존재. 출처 이름도 뒤섞여 있음:

| 범례 | 출처 표기 | 실제 출처 | 상태 |
|------|---------|---------|------|
| ① | Bloomberg | 뉴스타운 기사 내용 | ❌ 틀림 |
| ② | Bloomberg | 뉴스타운 기사 내용 | ❌ 틀림 |
| ③ | 아시아경제 | Bloomberg 기사 내용 | ❌ 틀림 |
| ④ | 아시아경제 | Bloomberg 기사 내용 | ❌ 틀림 |
| ... | ... | ... | 13개 전부 ❌ |

**이상적 결과**: ①=Bloomberg, ②=아시아경제, ③=뉴스타운, ④=IT동아, ⑤=출처불명 (5개만)

### 근본 원인 분석

팩트 추출이 **두 번** 일어나는 구조가 문제:

```
1단계: 기사별 크롤링 → GPT가 기사별로 팩트 추출 (analysis.facts)
       → 여기서는 기사 인덱스(i)를 확실히 안다!

2단계: _structure_facts()에서 전체 기사를 합쳐서 GPT에게 다시 추출 요청
       → GPT가 source_indices를 "추측"으로 매핑 ← 여기서 틀림!
       → Bloomberg 기사 팩트를 아시아경제로 잘못 매핑
       → 뉴스타운 기사 팩트를 Bloomberg로 잘못 매핑

3단계: Writer & Worker가 잘못된 source_indices 기반으로 ①②③ 매핑
       → 결과적으로 인용 번호와 출처 이름 둘 다 뒤죽박죽
```

**핵심**: 1단계에서 정확한 인덱스를 알고 있는데, 2단계에서 그걸 버리고 GPT에게 다시 추측하라고 시킴.

### ✅ 최종 해결: 기사별 확정 인덱스 하드코딩

GPT 추측을 제거하고, 기사 크롤링 시 이미 확실히 아는 인덱스를 각 팩트에 하드코딩.

#### 변경 1: `BE/src/script_gen/nodes/news_research.py`

**Before**: `_structure_facts(full_articles)` — GPT가 source_indices를 추측
```python
structured_facts = _structure_facts(full_articles)  # GPT 추측
```

**After**: 기사별 `analysis.facts`에서 확정 인덱스로 수집
```python
structured_facts = []
for i, art in enumerate(full_articles):
    art_facts = art.get("analysis", {}).get("facts", [])
    source_name = art.get("source", "Unknown")
    for fact_text in art_facts:
        structured_facts.append({
            "id": f"fact-{uuid.uuid4().hex[:12]}",
            "content": fact_text,
            "source_index": i,           # 확정된 기사 인덱스 (0, 1, 2, ...)
            "source_name": source_name,   # 출처명 (Bloomberg, 아시아경제, ...)
            "source_indices": [i],        # 기존 Writer 호환용
            "article_id": article_id,
            "article_url": article_url,
        })
```

#### 변경 2: `BE/src/script_gen/nodes/writer.py`

**Before**: `source_indices[0]`으로 기사 인덱스 획득 (GPT 추측값)
```python
source_indices = f.get("source_indices", [])
art_idx = source_indices[0] if source_indices and isinstance(source_indices[0], int) else i
```

**After**: 확정된 `source_index`를 우선 사용 + 출처명도 GPT에게 전달
```python
art_idx = f.get("source_index")  # 확정값 우선
if art_idx is None:
    # 호환: 기존 source_indices fallback
    source_indices = f.get("source_indices", [])
    art_idx = source_indices[0] if source_indices and isinstance(source_indices[0], int) else i

# GPT에게 출처명도 전달
source_label = f.get("source_name", "")
f_str += f"- {marker} [{f.get('id')}] ({source_label}) {f.get('content')}\n"
```

#### 변경 3: `BE/app/worker.py`

프론트엔드 인용 범례 생성 시에도 동일하게 `source_index`와 `source_name` 우선 사용:

```python
art_idx = fact.get("source_index")  # 확정값 우선

if art_idx is not None and 0 <= art_idx < len(articles):
    source_article = articles[art_idx]
else:
    # 호환: 기존 source_indices fallback
    ...

source_display = fact.get("source_name") or (source_article.get("source", "Unknown") ...)
```

### 기대 결과

```
Before (13개, 뒤죽박죽):
① Bloomberg — 세상이 위험에 처해 있다 (실제: 뉴스타운) ❌
② Bloomberg — 샤르마 사임 (실제: 뉴스타운) ❌
③ 아시아경제 — 고객 30만 (실제: Bloomberg) ❌
...⑬까지 전부 틀림

After (5개, 정확):
① Bloomberg — 고객 30만, API 매출 31억, 260억/700억 전망...
② 아시아경제 — 모델 출시 주기 2~3개월, 수십명 인간 대체...
③ 뉴스타운 — 세상이 위험에 처해 있다, 샤르마 퇴임...
④ IT동아 — GPT-5.3-코덱스 출시, ARC-AGI 2 68.8%...
⑤ 출처불명 — 알타비스타 스토리...
```

---

## 📌 문제 3: ① 클릭하면 3번 기사가 뜨는 버그

### 증상

인용 번호 ①을 클릭하면 1번 기사가 아니라 **3번 기사(뉴스타운)** 가 하이라이트됨.

### 근본 원인: `full_articles.sort()` 순서 충돌

```python
# STEP 1: 팩트 수집 — 원래 순서 기준으로 source_index 부여
for i, art in enumerate(full_articles):  # [A, B, C, D, E]
    source_index: i  # 0=A, 1=B, 2=C ...

# STEP 2: 기사 정렬 — 순서가 바뀜!
full_articles.sort(...)  # [C, A, D, B, E] (차트 많은 순서)

# STEP 3: worker.py에서—
articles[source_index=0]  # → C를 가져옴 (원래 A여야 함) ❌
```

`source_index`는 정렬 **전** 순서인데, `articles` 배열은 정렬 **후** 순서. 인덱스가 어긋남.

### ✅ 해결: 정렬을 팩트 수집 전으로 이동

```python
# Before (버그):
팩트 수집(index 0=A) → 정렬(articles[0]=C) → 불일치 ❌

# After (수정):
정렬(articles[0]=C) → 팩트 수집(index 0=C) → 일치 ✅
```

### 놓친 이유

팩트 수집 로직에만 집중하다가, **바로 아래에 있던 `sort()` 라인**과의 상호작용을 놓침. 데이터 흐름의 순서 검증이 부족했음.

---

## 📌 문제 4: 스크립트가 기사 5개 중 2개만 사용

### 증상

기사 5개 모두 팩트가 잘 뽑혀있는데, 스크립트의 인용 출처에는 **뉴스타운**과 **Jeremy Kahn** 2개만 존재.

### 근본 원인: `_structure_facts()`의 `combined_text[:10000]` 잘림

기존 `_structure_facts()` 함수는 5개 기사의 `summary`를 합쳐서 GPT에게 보내는데, **10000자로 잘림**:

```python
# 기존 _structure_facts() line 967
{combined_text[:10000]}  # ← 10000자 초과분 잘림!
```

| 기사 | summary 길이 | 누적 | 포함 |
|------|-------------|------|------|
| Article 0 | ~3000자 | 3000자 | ✅ |
| Article 1 | ~4000자 | 7000자 | ✅ |
| Article 2 | ~3000자 | **10000자 초과** | ❌ 잘림 |
| Article 3 | ~3000자 | - | ❌ 안 보임 |
| Article 4 | ~2000자 | - | ❌ 안 보임 |

GPT는 잘린 텍스트에서만 팩트를 뽑으니까 Article 0, 1만 사용.

### ✅ 해결: `_structure_facts()` 제거, `analysis.facts` 직접 수집

새 코드는 기사별 `analysis.facts`(이미 잘 뽑혀있는 팩트)를 GPT 없이 직접 수집. 잘림 없이 5개 기사 전부 포함.

---

## 📌 문제 5: `uuid` import 누락 (런타임 에러 위험)

### 증상

최종 코드 검증 시 발견. 실행하면 `NameError: name 'uuid' is not defined` 에러 발생 예정이었음.

### 원인

새 코드(line 85)에서 `uuid.uuid4()`를 사용하는데, `import uuid`가 파일 상단이 아닌 **line 435**에 있었음. Python은 파일을 위에서 아래로 실행하므로 함수 정의 시점에는 문제 없지만, 안전성을 위해 상단으로 이동.

### ✅ 해결

`import uuid`를 파일 상단 import 블록(line 18)에 추가.

---

## 📌 개선: `facts[:20]` → `facts[:35]` 확장

### 문제

Writer와 Worker에서 팩트를 최대 20개만 사용. 기사 5개 × 5~7팩트 = 25~35개인데, 20개 제한 때문에 **마지막 기사 팩트가 잘릴 수 있음**.

### ✅ 해결

`facts[:20]` → `facts[:35]`로 확장. Writer(Claude 확장 사고 모드)는 컨텍스트 여유 충분.

참고: 35개 팩트는 "메뉴판"이고, GPT가 스크립트에 실제로 인용하는 건 10~15개 정도. 나머지는 자연스럽게 안 쓰임.

---

## � 프론트엔드 변경: 인용 시스템 UI 구현

### 변경 1: `EditableWithCitations` 컴포넌트 신규 작성

**파일**: `FE/src/pages/script/components/script-editor.tsx`

기존 `<Textarea>` → `<EditableWithCitations>` 교체. 핵심 기능 2가지:

1. **편집 가능**: `contentEditable` div로 스크립트 직접 수정 가능
2. **①②③ 클릭 가능**: 인용 마커가 클릭 가능한 뱃지로 렌더링, 클릭 시 해당 기사 하이라이트

```
텍스트 → HTML 변환: ①②③ 문자를 정규식으로 찾아 <span class="cite-badge"> 뱃지로 교체
HTML → 텍스트 추출: 편집 시 뱃지를 다시 ①②③ 문자로 복원
클릭 핸들러: .cite-badge 클릭 → data-url 읽기 → onCitationClick(url) 호출
```

적용 위치: **인트로 / 본문 / 아웃트로 / 전체 보기** 총 4곳 모두 교체.

### 변경 2: 인용 범례 (Citation Legend) 추가

**파일**: `FE/src/pages/script/components/script-editor.tsx`

스크립트 하단에 인용 출처 범례 표시:

```
📌 인용 출처
① Bloomberg — 현재 앤트로픽은 1,830억 달러로 평가받고...
② 아시아경제 — GPT-5.3-코덱스와 클로드 오퍼스 4.6은...
③ 뉴스타운 — 모리닉 샤르마가 앤트로픽에서 사임을...
```

### 변경 3: 기사 하이라이트 (인용 클릭 연동)

**파일**: `FE/src/pages/script/components/related-resources.tsx`

- `activeCitationUrl` prop 추가
- `urlsMatch()` 헬퍼 함수: URL 도메인+경로 기준으로 비교 (쿼리 파라미터 차이 무시)
- `ArticleCard`에 `isHighlighted` prop 추가: 해당 기사 카드에 보라색 테두리 + 배경 표시
- 기사 제목 클릭 시 원본 기사 새 탭 열기 + 외부 링크 아이콘 추가

### 변경 4: Citation 타입 및 상태 관리

**파일**: `FE/src/lib/api/services/script-gen.service.ts`, `FE/src/pages/script/page.tsx`

- `Citation` 인터페이스 정의: `marker`, `number`, `fact_id`, `content`, `source`, `source_url` 등
- `ScriptHistoryItem`에 `citations` 필드 추가 (이전 결과 복원 시 인용 데이터도 복원)
- `page.tsx`에 `citations`, `activeCitationUrl` state 추가
- 생성 완료 시 `setCitations(result.citations || [])` 저장
- `topicId` URL 반영으로 새로고침 시 결과 복원

### 프론트엔드 데이터 흐름

```
① 클릭 → data-url="https://..." → onCitationClick(url)
         → setActiveCitationUrl(url)
         → RelatedResources(activeCitationUrl=url)
         → urlsMatch(url, article.url) → true
         → ArticleCard(isHighlighted=true) → 보라색 테두리
```

---

## 📌 1차 테스트 결과 분석 & 추가 수정

### 1차 테스트 결과 (문제 발견)

| 마커 | 스크립트 사용 | 범례 표시 | 문제 |
|------|-------------|----------|------|
| ① Wired | ✅ ~10회 | ✅ 12개 | 정상 (편중) |
| ② 아시아경제 | ✅ ~5회 | ✅ 7개 | 정상 |
| ③ 뉴스타운 | ❌ 0회 | ✅ 9개 | **안 쓰는데 범례에 있음** |
| ④ IT동아 | ❌ 0회 | ✅ 7개 | **안 쓰는데 범례에 있음** |
| ⑤ 5번 기사 | ❌ 없음 | ❌ 없음 | **facts[:35]로 잘림** |

**총 팩트**: 12+7+9+7 = 35개 → 딱 35개 채워서 5번 기사 팩트 전부 잘림

### 추가 수정 1: 팩트 제한 제거

- `writer.py`: `facts[:35]` → `facts` (제한 없음)
- `worker.py`: `structured_facts[:35]` → `structured_facts` (제한 없음)
- 이유: 5개 기사 × 최대 12팩트 = ~60개, Claude 컨텍스트로 충분히 처리 가능

### 추가 수정 2: 모든 출처 골고루 인용 규칙

- `writer.py` 인용 규칙에 추가:
```
⚠️ **모든 출처를 최소 1회 이상 인용하세요.** 특정 기사에 편중되지 않도록 골고루 인용합니다.
```
- GPT가 ①② 팩트만 편중 사용하던 문제 해결

### 추가 수정 3: 범례 필터링 (사용된 마커만 표시)

- `worker.py`: 스크립트 전체 텍스트(hook + chapters + outro)에서 실제 등장하는 마커(①②③...)만 찾아서 해당 팩트만 범례에 포함
- 스크립트에서 안 쓴 ③④ 팩트가 범례에 나오던 버그 수정
- fallback: 마커를 하나도 못 찾으면 전체 표시 (안전장치)

---

## 📁 수정된 파일 목록 (최종)

| 파일 | 변경 | 목적 |
|------|------|------|
| **백엔드** | | |
| `BE/src/script_gen/nodes/writer.py` | SystemMessage 3곳 "닫힌 책" 모드로 교체 | 할루시네이션 방지 |
| `BE/src/script_gen/nodes/writer.py` | `source_index` 우선 사용 + 출처명 전달 | 인용 번호 정확도 |
| `BE/src/script_gen/nodes/writer.py` | `facts[:35]` → 제한 제거 + "모든 출처 최소 1회" 규칙 | 팩트 커버리지 + 골고루 인용 |
| `BE/src/script_gen/nodes/news_research.py` | `_structure_facts()` → 기사별 확정 인덱스 수집 | 인용 번호 정확도 |
| `BE/src/script_gen/nodes/news_research.py` | `sort()` → 팩트 수집 전으로 이동 | ① 클릭 시 올바른 기사 표시 |
| `BE/src/script_gen/nodes/news_research.py` | `import uuid` 상단으로 이동 | 런타임 에러 방지 |
| `BE/app/worker.py` | `source_index`, `source_name` 우선 사용 | 프론트엔드 인용 범례 정확도 |
| `BE/app/worker.py` | `facts[:35]` → 제한 제거 + 사용된 마커만 범례 표시 | 5번 기사 누락 + 범례 버그 수정 |
| **프론트엔드** | | |
| `FE/src/pages/script/components/script-editor.tsx` | `Textarea` → `EditableWithCitations` 교체 (4곳) | 편집 + 인용 클릭 |
| `FE/src/pages/script/components/script-editor.tsx` | 인용 범례(Citation Legend) 추가 | ①②③ → 출처 매핑 표시 |
| `FE/src/pages/script/components/related-resources.tsx` | `isHighlighted` + `urlsMatch()` 추가 | 인용 클릭 시 기사 하이라이트 |
| `FE/src/pages/script/components/related-resources.tsx` | 기사 제목 클릭 → 원본 열기 + 외부 링크 아이콘 | 기사 원문 접근성 |
| `FE/src/lib/api/services/script-gen.service.ts` | `Citation` 인터페이스 + API 타입 추가 | 인용 데이터 타입 정의 |
| `FE/src/pages/script/page.tsx` | `citations` state + `activeCitationUrl` 연동 | 인용 클릭 상태 관리 |

---

## 💡 핵심 교훈

### 1. "하지 마" vs "넌 못 한다" — 프롬프트 심리학

GPT에게 `"이 정보를 추가하지 마세요"`라고 하면, GPT는 자기가 그 정보를 **알고 있기 때문에** 규칙을 어기고 추가할 수 있다. 반면 `"당신은 자체 지식이 없습니다"`라고 역할 자체를 제한하면, GPT는 규칙을 어길 동기가 사라진다.

👉 **금지(prohibition)보다 역할 제한(role restriction)이 효과적**

### 2. "GPT에게 맡기기" vs "코드로 확정하기"

`source_indices`를 GPT에게 추측하라고 시키면 50% 이상 틀린다. 이미 코드에서 확실히 아는 값(`enumerate(articles)`)을 하드코딩하면 100% 정확하다.

👉 **확실히 아는 값은 GPT에게 맡기지 말고 코드로 확정할 것**

### 3. BAD/GOOD 예시의 힘

단순한 규칙보다 구체적인 BAD/GOOD 예시를 보여주는 것이 GPT 모델의 행동을 더 효과적으로 제어한다. 특히 Few-shot 형태의 예시는 모델이 패턴을 인식하는 데 강력하다.

### 4. 데이터 흐름 순서 검증의 중요성

코드를 수정할 때 해당 함수 내부만 보면 안 된다. **앞뒤 코드와의 상호작용**(특히 `sort()`, 배열 인덱스, 데이터 전달 순서)을 반드시 추적해야 한다. `sort()`가 인덱스를 어긋나게 만든 버그는 단위 테스트로는 잡기 어렵고, **전체 데이터 흐름 추적**으로만 발견 가능하다.

### 5. 최종 검증에서 Import 확인

새 코드에서 사용하는 모듈(`uuid` 등)이 파일 상단에 import 되어있는지 반드시 확인. Python은 중간에 import해도 동작하지만, 함수 호출 시점에 따라 에러가 날 수 있다.

---

## ⏭️ 다음 단계

- [ ] Celery Worker 재시작 후 전체 파이프라인 테스트
- [ ] 인용 번호(①②③④⑤)가 기사 5개와 정확히 매핑되는지 확인
- [ ] ① 클릭 시 올바른 기사가 하이라이트 되는지 확인
- [ ] 할루시네이션 재발 여부 모니터링
- [ ] (선택) Verifier Phase 3에 자동 교정 기능 추가 (보험용)
