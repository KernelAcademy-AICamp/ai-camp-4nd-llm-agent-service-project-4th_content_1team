# 온보딩 플로우 UX 상세 기획서

## 목차
1. [전체 플로우 개요](#1-전체-플로우-개요)
2. [분기 처리 로직](#2-분기-처리-로직)
3. [초보 퍼널 - 4단계 입력](#3-초보-퍼널---4단계-입력)
4. [채널 분석 로딩 화면](#4-채널-분석-로딩-화면)
5. [채널 분석 결과 화면](#5-채널-분석-결과-화면)
6. [CSS 스타일 가이드](#6-css-스타일-가이드)

---

## 1. 전체 플로우 개요

```
OAuth 로그인 (Google 계정 = 유튜브 계정)
  ↓
분기 전 3가지 확인: 유튜브 계정 여부 · 채널 여부 · 영상 여부
  ↓
채널·영상 있을 때만 영상 길이/개수 조회
  ├─ 분기 1 (숙련 퍼널): Step 1-4 생략, 자동 분석 → 결과 → 탐색
  └─ 분기 2 (초보 퍼널): Step 1-4 입력 → 분석 로딩 → 결과 → 탐색
```

### Quota 사용량
- 영상 길이 조회: 2 quota
- 영상 개수 조회: 1 quota (영상 < 90분일 때만)
- 최선: 2 quota / 최악: 3 quota

---

## 2. 분기 처리 로직

분기 전에 **OAuth 로그인 시점**에 다음 3가지를 고려한다.

1. **유튜브 계정 여부** — Google 계정 = 유튜브 계정 (OAuth로 로그인한 계정)
2. **채널 여부** — 해당 계정에 연결된 YouTube 채널 존재 여부
3. **영상 여부** — 채널에 공개 영상이 있는지 (영상 길이·개수 조회 대상)

- **분기 1 (숙련 퍼널)**: 채널·영상이 있고, 영상 기준을 충족하는 경우
- **분기 2 (초보 퍼널)**: 채널 없음, 영상 없음, 또는 영상 기준 미충족

### 분기 조건 요약

| 유튜브 계정 | 채널 | 영상 | 결과 |
|------------|------|------|------|
| O | O | O | 영상 길이·개수 조회 후 판단 (아래 참고) |
| O | X | X | **분기 2** (초보) |
| O | O | X | **분기 2** (초보) |

**채널 O · 영상 O**인 경우에만 아래 기준 적용:

| 영상 길이 | 영상 개수 | 결과 |
|----------|----------|------|
| 90분 이상 | — | **분기 1** (숙련, 개수 조회 생략) |
| 90분 미만 | 50개 이상 | **분기 1** (숙련) |
| 90분 미만 | 50개 미만 | **분기 2** (초보) |

### 처리 순서 (채널 O · 영상 O일 때)

```typescript
// 사전: OAuth 로그인 → 유튜브 계정 O 전제
// 채널 없음 or 영상 없음 → 즉시 { type: "beginner" }

// Step 1: 영상 길이 조회 (Quota: 2)
const totalDuration = await getRecentVideosDuration()

if (totalDuration >= 90) {
  // 바로 숙련 퍼널 (개수 조회 생략)
  return { type: "experienced" }
}

// Step 2: 영상 < 90분일 때만 개수 확인 (Quota: 1)
const videoCount = await getChannelVideoCount()

if (videoCount >= 50) {
  return { type: "experienced" }
} else {
  return { type: "beginner" }
}
```

### 결과 정리
- **분기 1 (숙련 퍼널)**: 유튜브 계정 O · 채널 O · 영상 O 이면서 (영상 >= 90분 OR 개수 >= 50개)
- **분기 2 (초보 퍼널)**: 유튜브 계정 O · 채널 X · 영상 X **OR** 채널 O · 영상 X **OR** 채널 O · 영상 O 이면서 (영상 < 90분 AND 개수 < 50개)

---

## 3. 초보 퍼널 - 4단계 입력

### 중요 변경사항

1. **Step 3-4 순서**: 지향 유튜버(step-benchmark-channels) → 채널 방향성(step-channel-concept)
2. **지향 유튜버**: 선택 항목 (0개 가능). URL 입력 대신 **[분석] 메뉴의 기존 채널 분석 기능** 활용 (유효성 검사 없을 때 Quota 소진 리스크 존재)
3. **채널 방향성 키워드**: 주제/분위기 키워드(topic_keywords, style_keywords)는 **사용자가 선택한 카테고리 기반** 일반 키워드로 추천
4. **연령대(age_group)**: Slider → **버튼 방식** (단일 선택)
5. **성별(gender)**: 남성/여성 외 **"무관"** 추가
6. **본인 채널 분석 후**: 경쟁 채널 분석은 **백그라운드 실행** (결과 화면은 본인 채널 분석 완료 후 즉시 표시)
7. **추천 주제 유형**: 경쟁사 분석 기반(차별화 기회)은 **필수 아님** — 경쟁 채널 미선택 시에도 나머지 3가지 유형으로 추천 가능

### 공통 사항

**레이아웃**:
- HeaderOnlyLayout (사이드바 없음)
- max-w-[800px] 중앙 정렬
- px-4 (mobile), px-6 (desktop)

**버튼**:
- "이전" (Step 2부터)
- "다음" (검증 통과 시 활성화)
- 화살표 없음

**Step 표시**:
- [Step X/4] (상단 좌측 또는 중앙)

---

### Step 1: 카테고리 선택 (step-category-select.tsx)

#### 목적
선호하는 콘텐츠 카테고리를 선택하여 맞춤 분석의 기초 데이터 수집

#### 입력 항목

**카테고리** (9개):
```tsx
const CATEGORIES = [
  { id: "gaming", label: "게임", icon: "gaming.png" },
  { id: "education", label: "교육/정보", icon: "education.png" },
  { id: "food", label: "먹방/요리", icon: "food.png" },
  { id: "fitness", label: "운동/건강", icon: "fitness.png" },
  { id: "art", label: "예술/창작", icon: "art.png" },
  { id: "music", label: "음악", icon: "music.png" },
  { id: "vlog", label: "브이로그", icon: "vlog.png" },
  { id: "business", label: "비즈니스", icon: "business.png" },
  { id: "entertainment", label: "엔터테인먼트", icon: "entertainment.png" },
]
```

#### UI
- 그리드: 3x3 (mobile: 2x3)
- 이미지: `/images/categories/{icon}`
- 선택: 최소 1개, 최대 2개
- 시각적 피드백: border-primary + bg-primary/10 (선택 시)

#### Props
```tsx
interface StepCategorySelectProps {
  onNext: (categories: string[]) => void
  initialData?: string[]
}
```

#### 검증
- 1개 이상 선택 시 "다음" 활성화
- 2개 초과 선택 시 toast error

---

### Step 2: 타겟 유저 (step-target-audience.tsx)

#### 목적
주요 타겟 시청자의 성별과 연령대를 정의

#### 입력 항목

**성별** (필수):
```tsx
const GENDER_OPTIONS = [
  { value: "male", label: "남성" },
  { value: "female", label: "여성" },
  { value: "any", label: "무관" },  // 추가
]
```
- UI: Radio Group
- 기본값: 없음 (선택 필수)

**주 타겟 연령대** (필수):
```tsx
const AGE_CONFIG = {
  MIN: 10,
  MAX: 50,
  STEP: 10,
  N: 5,  // 10, 20, 30, 40, 50
}

const AGE_OPTIONS = [
  { value: 10, label: "10대" },
  { value: 20, label: "20대" },
  { value: 30, label: "30대" },
  { value: 40, label: "40대" },
  { value: 50, label: "50대+" },
]
```
- **UI 변경**: ~~Range Slider~~ → Button Group
- 단일 값 선택 (예: 30대)
- 버튼 형태로 5개 옵션 표시

#### Props
```tsx
interface StepTargetAudienceProps {
  onNext: (data: { gender: "male" | "female" | "any", ageGroup: number }) => void
  onPrev: () => void
  initialData?: { gender?: "male" | "female" | "any", ageGroup?: number }
}
```

#### 검증
- 성별 + 연령대 모두 선택 시 "다음" 활성화

---

### Step 3: 지향 유튜버 (step-benchmark-channels.tsx) — 선택 사항

#### 목적
참고할 유튜버 채널을 지정하여 경쟁 분석·벤치마킹에 활용 (0개 선택 가능)

#### 입력 방식

**URL 입력 없음**. **[분석] 메뉴의 기존 채널 분석 기능** 활용:
- 사용자가 이미 [분석]에서 등록·분석한 채널 목록에서 선택
- 또는 분석 화면에서 채널 검색 후 선택

**리스크**: 유효성 검사 없이 기존 채널 ID만 사용할 경우 잘못된 요청으로 **Quota 소진** 가능성이 있음. 필요 시 채널 존재/접근 가능 여부 검증 권장.

#### UI - Chip 형태

**구성** (선택된 채널 표시):
```
┌─────────────────────────────────────┐
│ [김] 게임왕 김철수 @game...      [×] │
└─────────────────────────────────────┘
```

**Avatar** (첫 글자 기반), **채널명**: 16자 이후 말줄임

#### Props
```tsx
interface StepBenchmarkChannelsProps {
  onNext: (channels: BenchmarkChannel[]) => void
  onPrev: () => void
  initialData?: BenchmarkChannel[]
}

interface BenchmarkChannel {
  channelId: string
  title: string
  customUrl?: string
  subscriberCount?: number
  videoCount?: number
}
```

#### 검증
- **최소: 0개** (선택 사항)
- 최대: 3개
- "다음"은 별도 필수 조건 없이 활성화 (0개여도 진행 가능)

#### API
- 기존 [분석] 채널 목록/검색 API 활용

---

### Step 4: 채널 방향성 (step-channel-concept.tsx)

#### 목적
채널의 주제와 분위기를 정의하여 페르소나 생성 완성

#### 입력 항목

**주제 키워드** (topic_keywords):
- 선택: 최소 1개, 최대 5개
- UI: Chip 선택 (다중)
- **소스: 사용자가 Step 1에서 선택한 카테고리(category) 기반 추천** — 해당 카테고리에 맞는 일반적인 키워드 목록 제공

**분위기 키워드** (style_keywords):
- 선택: 최소 1개, 최대 5개
- UI: Chip 선택 (다중)
- **소스: 동일하게 선택한 카테고리 기반 추천** — 일반적인 분위기 키워드

#### Chip UI
```tsx
// 선택 안 됨
className="bg-muted border-border text-muted-foreground"

// 선택됨
className="bg-primary/10 border-primary text-primary"
<Check className="w-4 h-4 mr-2" />
```

**말줄임**: 12자 이후 ...

#### Props
```tsx
interface StepChannelConceptProps {
  onNext: (data: {
    topicKeywords: string[]
    styleKeywords: string[]
  }) => void
  onPrev: () => void
  initialData?: { topicKeywords?: string[], styleKeywords?: string[] }
  suggestedKeywords: { topics: string[], styles: string[] }  // category 기반
}
```

#### 검증
- 주제 1개 이상 AND 분위기 1개 이상 선택 시 "다음" 활성화

---

## 4. 채널 분석 로딩 화면 (loading-channel-analysis.tsx)

### Agentic UX 구성

- **표시 범위**: **내 채널 분석** 진행만 표시. 경쟁 채널 분석은 백그라운드에서 실행되며 **프론트에는 노출하지 않음**.
- **UI 크기**: 전체 화면이 아닌 **Popover 수준** (작은 패널). 진행률·단계는 한눈에 보이되 화면을 가득 채우지 않음.

#### Progress UI (Popover 크기)

```tsx
{/* Popover/패널 크기: max-w-[320px] 또는 w-80 수준, 필요 시 화면 중앙 또는 상단 고정 */}
<div className="rounded-lg border bg-card p-4 shadow-lg max-w-[320px] w-full">
  {/* Progress Bar */}
  <div className="mb-3">
    <div className="flex justify-between text-xs mb-1">
      <span>분석 진행률</span>
      <span>{progress}%</span>
    </div>
    <div className="w-full bg-muted rounded-full h-1.5">
      <div className="bg-primary h-1.5 rounded-full" style={{ width: `${progress}%` }} />
    </div>
    <div className="text-[10px] text-muted-foreground mt-0.5">
      예상 남은 시간: {estimatedTime}초
    </div>
  </div>
  
  {/* Timeline - 내 채널 분석만 (경쟁 채널 분석은 백그라운드, UI 미표시) */}
  <div className="space-y-1.5">
    <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">내 채널 분석</p>
    <StepItem status="completed" icon={Search} label="채널 정보 수집" time="3초" />
    <StepItem status="processing" icon={FileText} label="영상 데이터 읽는 중" detail="최신 50개 영상 로드 중..." />
    <StepItem status="pending" icon={BarChart} label="영상 패턴 분석 대기" />
    <StepItem status="pending" icon={MessageSquare} label="시청자 반응 분석 대기" />
    <StepItem status="pending" icon={Brain} label="페르소나 생성 대기" />
    <StepItem status="pending" icon={Check} label="결과 저장 대기" />
  </div>
</div>
```

- **배치**: 로딩 중인 메인 화면 위에 작은 패널로 띄우거나, 상단/코너에 고정. 전체 레이아웃은 `min-h-screen` 없이 기존 페이지 흐름 유지 가능.

#### 단계 아이콘

| 상태 | 아이콘 | 색상 |
|------|--------|------|
| completed | Check | green |
| processing | Loader2 (spin) | primary |
| pending | Clock | muted |

#### 폴링 로직
```tsx
useEffect(() => {
  const interval = setInterval(async () => {
    const status = await checkAnalysisStatus(taskId)
    setProgress(status.progress)
    updateSteps(status.currentStep)
    
    if (status.completed) {
      clearInterval(interval)
      onComplete(status.result)
    }
  }, 2000)  // 2초 간격
  
  return () => clearInterval(interval)
}, [taskId])
```

---

## 5. 채널 분석 결과 화면 (channel-analysis-result.tsx)

### 화면 구성

#### Header
```tsx
<div>
  <Badge>Channel Analysis Complete</Badge>
  <h1>{channelName}</h1>
  <p>채널을 분석했어요. 앞으로 이렇게 도와드릴게요.</p>
  <div>
    {mainTopics.map(tag => <Tag>{tag}</Tag>)}
    <Button variant="ghost" size="sm">수정</Button>
  </div>
</div>
```

**데이터**:
- `channel.title`
- `persona.main_topics`

---

#### Section 1: 톤앤매너

**제목**: "이 톤으로 스크립트를 써드릴게요"
**부제**: "채널의 말투 패턴을 학습했어요"

**표시 내용**:
- 말투 샘플 (Chip 형태): `tone_samples`
- 토글: "어떻게 분석했나요?" → `tone_manner`

**UI**:
```tsx
<Card>
  {/* 말투 샘플 */}
  <div className="bg-primary/5 border border-primary/10 rounded-lg p-4 mb-4">
    {toneSamples.map(sample => (
      <span className="chip">{sample}</span>
    ))}
  </div>
  
  {/* 토글 */}
  <ToggleSection title="어떻게 분석했나요?">
    <p>{toneManner}</p>
  </ToggleSection>
</Card>
```

---

#### Section 2: 콘텐츠 구조

**제목**: "이 구조로 스크립트를 설계해드릴게요"
**부제**: "조회수가 높았던 영상의 공통 구조를 분석했어요"

**표시 내용**:
1. **성공 공식** (강조 박스)
   - `success_formula`
   - 그라데이션 배경 + 상단 accent line

**UI**:
```tsx
<Card>
  {/* 성공 공식 */}
  <div className="bg-gradient-to-r from-primary/10 to-green/5 border-primary/20 rounded-lg p-4 mb-4">
    <div className="h-0.5 bg-gradient-to-r from-primary to-green mb-3" />
    <p className="text-xs text-muted-foreground uppercase">성공 공식</p>
    <p className="font-semibold">{successFormula}</p>
  </div>
  
  {/* 토글 */}
  <ToggleSection title="어떻게 분석했나요?">
    <p>{structureDetail}</p>
  </ToggleSection>
</Card>
```

---

#### Section 3: 추천 주제 미리보기

**기획 요약**: 채널 분석 결과 화면에서 사용자에게 "앞으로 어떤 방식으로 주제를 추천받을 수 있는지" 미리 보여 주는 섹션. explore(탐색) 페이지의 4가지 주제 유형과 동일한 구성을 2x2 그리드로 노출하여, "이 분석 기반으로 주제 추천받기" CTA로 자연스럽게 연결.

**제목**: "이렇게 주제를 추천해드릴게요"
**부제**: "분석 결과를 바탕으로 4가지 방식으로 주제를 찾아드려요"

**표시 내용**: explore 페이지의 4가지 유형 카드 (2x2 그리드). **추천 주제 유형 중 경쟁사 분석 기반(차별화 기회)은 필수가 아님** — 지향 유튜버를 선택하지 않은 경우 해당 카드는 비활성/안내 문구로 표시하거나 제외 가능.

**UI**:
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  {/* 1. 성공 방정식 */}
  <TopicTypePreview 
    color="green"
    title="성공 방정식"
    detail="조회수가 높았던 영상의 패턴을 분석해서 유사한 주제를 추천해요"
  />
  
  {/* 2. 구독자 관심 */}
  <TopicTypePreview 
    color="blue"
    title="구독자 관심"
    detail="시청자들이 가장 궁금해하는 질문을 주제로 만들어요"
  />
  
  {/* 3. 최근 경향성 */}
  <TopicTypePreview 
    color="purple"
    title="최근 경향성"
    detail="최근 인기 있었던 영상 스타일로 새로운 시도를 제안해요"
  />
  
  {/* 4. 차별화 기회 */}
  <TopicTypePreview 
    color="amber"
    title="차별화 기회"
    detail="경쟁 채널 분석 결과 틈새 시장을 찾아드려요"
  />
</div>
```

**TopicTypePreview 컴포넌트**:
```tsx
<div className="p-4 rounded-lg border border-{color}/20 bg-{color}/5">
  <div className="flex items-center gap-2 mb-2">
    <div className="w-1 h-8 bg-gradient-to-b from-{color}-500 to-{color}-600 rounded" />
    <div>
      <div className="text-xs text-{color}-400 font-medium">{title}</div>
    </div>
  </div>
  <p className="text-xs text-muted-foreground">{detail}</p>
</div>
```

---

#### CTA

```tsx
<Button className="w-full" size="lg">
  이 분석 기반으로 주제 추천받기
</Button>

<p className="text-xs text-muted-foreground text-center mt-3">
  분석 결과는 언제든 수정할 수 있어요
</p>
```

---

## 6. CSS 스타일 가이드

### 공통 스타일

#### 배경색
```css
.bg-dark: #0B0B0F
.bg-card: rgba(255,255,255,0.03)
.border-card: rgba(255,255,255,0.06)
```

#### Typography
```css
font-family: 'Pretendard', -apple-system, sans-serif
font-family-mono: 'JetBrains Mono', monospace

heading-1: 26px, weight-800, letter-spacing -0.5px
heading-2: 18px, weight-700, letter-spacing -0.3px
body: 13.5-15px, line-height 1.75
```

#### 색상 팔레트

**Primary (보라)**:
```css
--primary: #6B5CFF
--primary-light: #A89BFF
--primary-bg: rgba(107,92,255,0.1)
--primary-border: rgba(107,92,255,0.2)
```

**주제 유형별**:
```css
--green: #46da7d → #19a74e
--blue: #3b82f6 → #1d4ed8
--purple: #a855f7 → #7e22ce
--amber: #fbbf24 → #f59e0b
```

#### Chip 스타일
```css
.chip {
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}

/* 선택 안 됨 */
background: rgba(255,255,255,0.04);
border: 1px solid rgba(255,255,255,0.08);
color: #9CA3AF;

/* 선택됨 */
background: rgba(107,92,255,0.1);
border: 1px solid rgba(107,92,255,0.2);
color: #A89BFF;
```

#### 토글 섹션
```css
.toggle {
  border-radius: 10px;
  transition: all 0.25s ease;
}

/* 닫힘 */
border: 1px solid rgba(255,255,255,0.05);
background: rgba(255,255,255,0.01);

/* 열림 */
border: 1px solid rgba(107,92,255,0.15);
background: rgba(107,92,255,0.02);
```

#### 애니메이션
```css
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

.anim { animation: fadeInUp 0.45s ease-out both; }
.d1 { animation-delay: 0.05s; }
.d2 { animation-delay: 0.12s; }
.d3 { animation-delay: 0.2s; }
.d4 { animation-delay: 0.28s; }
```

#### CTA 버튼
```css
.cta-btn {
  width: 100%;
  padding: 16px 24px;
  border-radius: 12px;
  background: linear-gradient(135deg, #2D2DFF, #6B5CFF);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.25s;
}

.cta-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 32px rgba(107,92,255,0.35);
}
```

---

## 7. 데이터 구조

### 온보딩 데이터 통합

```tsx
interface OnboardingData {
  // Step 1
  preferredCategories: string[]  // ["gaming", "education"]
  
  // Step 2
  targetGender: "male" | "female"
  targetAgeGroup: number  // 30
  
  // Step 3
  benchmarkChannels: BenchmarkChannel[]  // 1-3개
  
  // Step 4
  topicKeywords: string[]  // 1-5개
  styleKeywords: string[]  // 1-5개
}
```

### API 제출

```tsx
// Step 4 완료 후
POST /api/personas/generate
Body: OnboardingData

// 또는 각 단계별로 저장
PATCH /api/personas/me
Body: { step1Data, step2Data, ... }
```

---

## 8. 탐색 화면 연동 (Dummy → Real 전환)

### 플로우

```
1. 본인 채널 분석 완료 (65%)
   ↓
2. 채널 분석 결과 화면 즉시 표시
   ├─ 경쟁 채널 분석은 백그라운드에서 계속 실행 (사용자 대기 없음)
   └─ 결과 화면에서 바로 "이 분석 기반으로 주제 추천받기" 등 CTA 가능
   ↓
3. "시작하기" 클릭
   ↓
4. 탐색 화면 (explore)
   ├─ Dummy 주제 8개 즉시 표시
   └─ 상단 배너: "더 정확한 주제 준비 중..."
   ↓
5. 경쟁 분석 완료 (100%)
   ↓
6. Dummy → Real 주제로 교체 (fade)
   └─ 배너: "✨ 맞춤 주제가 준비되었어요!"
```

### Dummy 주제

```tsx
const DUMMY_TOPICS = [
  {
    id: "dummy-1",
    badge: "분석 중",
    title: "AI가 맞춤 주제를 찾고 있어요...",
    description: "경쟁 채널과 트렌드를 분석해서 최적의 주제를 추천해드릴게요!",
    hashtags: ["분석중", "잠시만기다려주세요"],
  },
  // ... 8개
]
```

### 전환 애니메이션
```tsx
<div className={cn(
  "transition-all duration-500",
  isAnalyzing && "opacity-60 pointer-events-none"
)}>
  <TopicCard {...topic} />
</div>
```

---

## 9. 파일 구조

```
FE/src/
├── components/
│   └── loading-channel-analysis.tsx  (신규)
│
└── pages/
    └── onboarding/
        ├── page.tsx                          (수정)
        └── components/
            ├── step-category-select.tsx      (신규)
            ├── step-target-audience.tsx      (신규)
            ├── step-benchmark-channels.tsx   (신규)
            ├── step-channel-concept.tsx      (신규)
            └── channel-analysis-result.tsx   (신규)
```

---

## 10. 반응형 대응

### Breakpoints
- Mobile: 393px (1열)
- Tablet: 1024px (1-2열)
- Desktop: 1920px (중앙 정렬)

### 컨테이너
```tsx
<div className="max-w-[800px] mx-auto px-4 py-8 md:px-6 md:py-12">
  {/* 스텝 콘텐츠 */}
</div>
```

**분석 결과 화면**:
```tsx
<div className="max-w-[640px] mx-auto px-5 py-10">
  {/* 결과 콘텐츠 */}
</div>
```

---

## 부록: Phase 2 (선택 구현)

### 채널 방향성 키워드 소스 (현행)

- **Step 4 채널 방향성**의 `topic_keywords`, `style_keywords`는 **Step 1에서 선택한 카테고리 기반** 일반 키워드로 추천 (별도 API 없이 프리셋 또는 정적 매핑 가능).

### 지향 유튜버 기반 키워드 추출 (나중에 구현 시)

**필요 API** (선택):
```python
POST /api/onboarding/extract-keywords-from-benchmarks
Body: { channel_ids: ["UC...", "UC...", "UC..."] }
Response: { 
  topic_keywords: ["개발", "코딩", ...],
  style_keywords: ["전문적", "실용적", ...]
}
```

- Step 3에서 지향 유튜버를 선택한 경우에만 호출하고, 그 결과를 Step 4 추천 키워드에 보강할 수 있음. 현재는 카테고리 기반만 사용.

---

완료!
