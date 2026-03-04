# 🎨 Orbiter 화면 구성 재설계 계획

---

## 📊 현재 vs 목표 화면 구조

### **현재 (AS-IS)**
```
Login
  ↓
Onboarding (1단계만)
  - 카테고리 선택
  ↓
Dashboard
  - 주제 추천
  - 캘린더
  - 확정 주제
  ↓
Script (스크립트 생성)
  - 경쟁 영상 분석
  - 관련 리소스
  ↓
Analysis (경쟁 채널만)
  - 경쟁 채널 검색/추가
  - 경쟁 영상 분석
  ↓
Thumbnail (썸네일 생성)
```

### **목표 (TO-BE)**
```
Login
  ↓
┌──────────────────────────────┐
│ Onboarding (확장)            │
├──────────────────────────────┤
│ 1. 맞춤 정보 수집            │
│    - 카테고리 선택           │
│    - 업로드 주기             │
│    - 타겟 청중               │
│ 2. 채널 분석 결과 (NEW)      │
│    - 자동 분석 진행          │
│    - 채널 성격 도출          │
│    - 구독자 특성 분석        │
└──────────────────────────────┘
  ↓
┌──────────────────────────────┐
│ 주제 탐색 (재구성)           │
├──────────────────────────────┤
│ - 주제 추천 섹션             │
│   ├─ AI 추천 주제            │
│   └─ 찜하기 기능 (NEW)       │
│ - 실시간 트렌드              │
│   ├─ 검색량 트렌드           │
│   └─ 커뮤니티 반응           │
└──────────────────────────────┘
  ↓
┌──────────────────────────────┐
│ 스크립트 (개선)              │
├──────────────────────────────┤
│ 탭 1: 새 스크립트 작성       │
│   - 찜한 주제 선택 (NEW)     │
│   - 직접 입력                │
│ 탭 2: 이전 스크립트 (NEW)    │
│   - 생성 이력 목록           │
│   - 재편집                   │
└──────────────────────────────┘
  ↓
┌──────────────────────────────┐
│ 스크립트 상세 (유지)         │
└──────────────────────────────┘
  ↓
┌──────────────────────────────┐
│ 채널 분석 (확장)             │
├──────────────────────────────┤
│ 탭 1: 내 채널 분석 (NEW)     │
│   - 내 채널 성격             │
│   - 내 구독자 분석           │
│   - 최근 영상 분석           │
│ 탭 2: 경쟁 채널 분석         │
│   - 경쟁 채널 추가 (최대 3개)│
│   - 경쟁 영상 분석           │
│   - AI 인사이트              │
└──────────────────────────────┘
  ↓
Thumbnail (썸네일 생성)
```

---

## 🎯 화면별 상세 설계

### **1️⃣ 온보딩 플로우 (2단계로 확장)**

#### **Step 1: 맞춤 정보 수집** (기존 + 확장)
```tsx
[현재 있음]
✅ 카테고리 선택 (9개 중 다중 선택)

[추가 필요]
⏸️ 업로드 주기 선택
   - 주 1회, 주 2-3회, 주 4-5회, 매일
   
⏸️ 타겟 청중 입력
   - 연령대: 10대, 20대, 30대, 40대 이상
   - 관심사: 자유 입력
   
⏸️ 채널 목표
   - 구독자 증가, 수익 창출, 브랜딩, 취미
```

**API 연동:**
```typescript
POST /api/personas/update
{
  categories: ["gaming", "education"],
  upload_frequency: "weekly_2_3",
  target_age_groups: ["20s", "30s"],
  interests: ["AI", "개발"],
  goals: ["subscriber_growth", "revenue"]
}
```

**UI 컴포넌트:**
- `<CategorySelector />` (기존)
- `<FrequencySelector />` (NEW)
- `<AudienceSelector />` (NEW)
- `<GoalSelector />` (NEW)

---

#### **Step 2: 채널 분석 결과** (신규)
```tsx
[AI 분석 진행 중]
🔄 "채널을 분석하고 있습니다..." (5-10초)

[분석 완료 화면]
✨ 분석 완료!

📊 내 채널 성격
   "친근하고 유머러스한 교육 콘텐츠"
   
👥 주요 구독자
   "20-30대 직장인, IT/개발에 관심"
   
💡 콘텐츠 특징
   - 실용적인 팁 중심
   - 편집 퀄리티 우수
   - 초보자 친화적
   
[다음 단계] 버튼 → Dashboard
```

**API 연동:**
```typescript
// Onboarding Step 1 완료 시 자동 호출
POST /api/personas/generate

// 응답 대기 (5-10초)
GET /api/personas/me → { analyzed_at, ... }

// 결과 표시
```

**기존 코드 활용:**
- `generatePersona()` - 이미 구현됨
- `PersonaResponse` 타입 - 이미 있음
- 로딩 UI - 이미 구현됨 (`isAnalyzing`)

**추가 필요:**
- 분석 결과 표시 UI
- 애니메이션 효과
- "다음" 버튼

---

### **2️⃣ 주제 탐색 화면** (Dashboard 재구성)

#### **현재 구조:**
```
Dashboard
  ├─ Sidebar (왼쪽)
  ├─ 캘린더 (중앙)
  └─ 주제 추천 섹션 (오른쪽)
      └─ RecommendationCards
```

#### **목표 구조:**
```
주제 탐색
  ├─ Sidebar (왼쪽)
  │
  ├─ 메인 섹션 (중앙-오른쪽, 넓게)
  │   │
  │   ├─ 섹션 1: AI 추천 주제
  │   │   ├─ 추천 카드 (6-10개)
  │   │   ├─ 각 카드:
  │   │   │   ├─ 제목
  │   │   │   ├─ 예상 시청 시간
  │   │   │   ├─ 트렌드 점수
  │   │   │   ├─ [찜하기] 버튼 ⭐ (NEW)
  │   │   │   └─ [스크립트 작성] 버튼
  │   │   └─ 페이지네이션
  │   │
  │   └─ 섹션 2: 실시간 트렌드
  │       ├─ 급상승 키워드 (5개)
  │       ├─ 커뮤니티 반응 높은 주제
  │       └─ 검색량 증가 주제
  │
  └─ 사이드 패널 (오른쪽, 접을 수 있음)
      ├─ 확정 주제 (캘린더)
      └─ 찜한 주제 (NEW)
          └─ 리스트 형태
```

**새로운 기능:**
```typescript
// 찜하기 기능
const handleBookmark = async (topicId: string) => {
  await api.post('/api/topics/bookmark', { topic_id: topicId })
  // 찜한 주제 목록에 추가
}

// 찜한 주제 목록 조회
const bookmarkedTopics = await api.get('/api/topics/bookmarked')
```

**DB 스키마 (추가 필요):**
```sql
CREATE TABLE bookmarked_topics (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  topic_id UUID REFERENCES content_topics(id),
  created_at TIMESTAMP,
  UNIQUE(user_id, topic_id)
);
```

---

### **3️⃣ 스크립트 화면** (탭 구조로 개선)

#### **현재 구조:**
```
Script Page
  ├─ 주제 입력 (직접 입력만)
  ├─ 경쟁 영상 분석
  ├─ 관련 리소스
  └─ 스크립트 편집기
```

#### **목표 구조:**
```
스크립트 페이지
  │
  ├─ Tabs (상단)
  │   ├─ [새 스크립트 작성]
  │   └─ [이전 스크립트] (NEW)
  │
  ├─ 탭 1: 새 스크립트 작성
  │   │
  │   ├─ 주제 선택 방법 (라디오 버튼)
  │   │   ├─ ○ 찜한 주제에서 선택 (NEW)
  │   │   │   └─ 드롭다운: [찜한 주제 1, 주제 2, ...]
  │   │   └─ ○ 직접 입력
  │   │       └─ <Input placeholder="주제를 입력하세요" />
  │   │
  │   ├─ [스크립트 생성 시작] 버튼
  │   │
  │   └─ 생성 진행 중...
  │       ├─ 프로그레스 바 (8단계)
  │       ├─ 경쟁 영상 분석
  │       ├─ 관련 리소스
  │       └─ 스크립트 편집기
  │
  └─ 탭 2: 이전 스크립트 (NEW)
      │
      ├─ 필터
      │   ├─ 날짜 범위
      │   ├─ 상태 (작성 중, 완료, 삭제)
      │   └─ 검색 (제목)
      │
      └─ 스크립트 카드 리스트
          ├─ 카드:
          │   ├─ 썸네일 (미리보기)
          │   ├─ 제목
          │   ├─ 주제
          │   ├─ 생성 날짜
          │   ├─ 상태
          │   └─ 액션
          │       ├─ [편집]
          │       ├─ [복사]
          │       └─ [삭제]
          └─ 페이지네이션
```

**API 연동:**
```typescript
// 찜한 주제 목록 (드롭다운용)
GET /api/topics/bookmarked
→ [{ id, title, ... }, ...]

// 이전 스크립트 목록
GET /api/scripts/history?page=1&limit=10
→ {
  total: 25,
  scripts: [
    {
      id: "uuid",
      title: "AI 트렌드 분석",
      topic: "인공지능",
      status: "completed",
      created_at: "2026-02-08",
      thumbnail_url: "..."
    },
    ...
  ]
}

// 스크립트 재편집
GET /api/scripts/{id}
→ { full_content, ... }
```

**DB 스키마 (확인 필요):**
- `script_outputs` 테이블 존재 여부 확인
- 필요 시 history 조회 API 추가

---

### **4️⃣ 스크립트 상세 화면** (유지)

**현재 구조:**
```
Script Detail
  ├─ Header
  │   ├─ 주제 표시
  │   └─ 상태 (작성 중/완료)
  │
  ├─ 경쟁 영상 분석
  │   └─ Competitor Analysis 컴포넌트
  │
  ├─ 관련 리소스
  │   └─ Related Resources 컴포넌트
  │
  └─ 스크립트 편집기
      └─ Script Editor 컴포넌트
```

**변경 불필요** ✅ (현재 구조 유지)

---

### **5️⃣ 채널 분석 화면** (탭 구조 확장) ⭐ 중요

#### **현재: Analysis Page (경쟁 채널만)**
```
Analysis
  ├─ Sidebar
  └─ Main
      ├─ 채널 검색
      ├─ 등록된 경쟁 채널 목록
      └─ 영상 분석 결과
```

#### **목표: 2-Tab 구조**

```
채널 분석 페이지
  ├─ Sidebar (왼쪽)
  │
  ├─ Tabs (상단)
  │   ├─ [내 채널 분석] (NEW)
  │   └─ [경쟁 채널 분석] (기존)
  │
  ├─ 탭 1: 내 채널 분석 (NEW)
  │   │
  │   ├─ 섹션 1: 채널 개요
  │   │   ├─ 썸네일, 이름, 구독자 수
  │   │   ├─ 마지막 업데이트 날짜
  │   │   └─ [재분석] 버튼
  │   │
  │   ├─ 섹션 2: 채널 성격 (Persona)
  │   │   ├─ 📝 채널 개성
  │   │   │   "친근하고 유머러스한 교육 콘텐츠"
  │   │   ├─ 🎨 콘텐츠 스타일
  │   │   │   "실용적 팁 중심, 초보자 친화적"
  │   │   └─ 🎯 타겟 청중
  │   │       "20-30대 직장인, IT 관심"
  │   │
  │   ├─ 섹션 3: 구독자 분석 (Analytics API)
  │   │   ├─ 📊 인구통계
  │   │   │   ├─ 연령대 분포 (차트)
  │   │   │   ├─ 성별 분포 (차트)
  │   │   │   └─ 국가별 분포
  │   │   ├─ 📈 시청 패턴
  │   │   │   ├─ 평균 시청 시간
  │   │   │   ├─ 이탈 시점
  │   │   │   └─ 재방문율
  │   │   └─ 🎬 선호 콘텐츠
  │   │       └─ 조회수 높은 영상 Top 5
  │   │
  │   └─ 섹션 4: 최근 영상 분석 (NEW)
  │       ├─ 최신 영상 3-5개
  │       ├─ 각 영상:
  │       │   ├─ 썸네일 + 제목
  │       │   ├─ 조회수/좋아요/댓글 수
  │       │   ├─ 📊 성과 분석
  │       │   │   ├─ 예상 대비 실제
  │       │   │   ├─ CTR, 평균 시청 시간
  │       │   │   └─ 구독자 전환율
  │       │   └─ 🤖 AI 인사이트
  │       │       ├─ 성공 요인
  │       │       ├─ 개선 포인트
  │       │       └─ 시청자 반응
  │       └─ [상세 보기] 버튼
  │
  └─ 탭 2: 경쟁 채널 분석 (기존 유지)
      │
      ├─ 경쟁 채널 검색 (기존)
      │
      ├─ 등록된 경쟁 채널 (최대 3개 제한 추가)
      │   └─ 3개 도달 시: "경쟁 채널은 최대 3개까지 등록 가능합니다"
      │
      ├─ 경쟁 영상 분석 (기존)
      │   └─ 최신 3개 영상 자동 분석
      │
      └─ AI 추천 경쟁 채널 (NEW)
          ├─ "분석할 만한 채널 추천"
          ├─ 추천 근거 표시
          └─ [추가] 버튼
```

**API 연동:**
```typescript
// 내 채널 분석
GET /api/personas/me
→ { channel_personality, target_audience, content_style, ... }

GET /api/channels/my/analytics
→ { demographics, viewing_patterns, top_videos, ... }

GET /api/channels/my/recent-videos
→ [{ video_id, title, stats, ai_insights, ... }]

// 경쟁 채널 추천 (NEW)
GET /api/channels/competitor/recommendations
→ [{ channel_id, title, reason, similarity_score }]
```

---

## 🗂️ 파일 구조 제안

### **신규 생성 필요한 파일**

```
FE/src/pages/
  │
  ├─ onboarding/
  │   ├─ page.tsx (기존)
  │   └─ components/ (NEW)
  │       ├─ step1-info-collection.tsx
  │       ├─ step2-analysis-result.tsx
  │       ├─ frequency-selector.tsx
  │       ├─ audience-selector.tsx
  │       └─ goal-selector.tsx
  │
  ├─ dashboard/ → explore/ (이름 변경 고려)
  │   ├─ page.tsx (재구성)
  │   └─ components/
  │       ├─ recommendation-cards.tsx (기존)
  │       ├─ bookmarked-topics-panel.tsx (NEW)
  │       └─ trend-section.tsx (NEW)
  │
  ├─ script/
  │   ├─ page.tsx (탭 구조로 재구성)
  │   └─ components/
  │       ├─ script-creation-tab.tsx (NEW)
  │       │   ├─ bookmarked-topic-selector.tsx (NEW)
  │       │   └─ direct-input-form.tsx
  │       ├─ script-history-tab.tsx (NEW)
  │       │   ├─ script-card.tsx
  │       │   └─ script-filters.tsx
  │       ├─ competitor-analysis.tsx (기존)
  │       ├─ related-resources.tsx (기존)
  │       └─ script-editor.tsx (기존)
  │
  └─ analysis/
      ├─ page.tsx (탭 구조로 재구성)
      └─ components/
          ├─ my-channel-tab.tsx (NEW)
          │   ├─ channel-personality-section.tsx
          │   ├─ subscriber-analytics-section.tsx
          │   └─ recent-videos-section.tsx
          ├─ competitor-tab.tsx (기존을 이동)
          │   ├─ channel-search.tsx
          │   ├─ registered-channels.tsx
          │   └─ recommended-channels.tsx (NEW)
          └─ video-analysis-card.tsx (공통)
```

---

## 🎨 UI/UX 개선 포인트

### **1. 찜하기 기능 (북마크)**
```tsx
// 주제 카드에 추가
<Card>
  <CardHeader>
    <div className="flex items-start justify-between">
      <CardTitle>{topic.title}</CardTitle>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => handleBookmark(topic.id)}
      >
        {isBookmarked ? (
          <Star className="w-4 h-4 fill-yellow-500 text-yellow-500" />
        ) : (
          <Star className="w-4 h-4" />
        )}
      </Button>
    </div>
  </CardHeader>
  ...
</Card>
```

### **2. 탭 전환 애니메이션**
```tsx
<Tabs defaultValue="my-channel" className="w-full">
  <TabsList>
    <TabsTrigger value="my-channel">
      <BarChart3 className="w-4 h-4 mr-2" />
      내 채널 분석
    </TabsTrigger>
    <TabsTrigger value="competitor">
      <Users className="w-4 h-4 mr-2" />
      경쟁 채널 분석
    </TabsTrigger>
  </TabsList>
  
  <TabsContent value="my-channel">
    <MyChannelTab />
  </TabsContent>
  
  <TabsContent value="competitor">
    <CompetitorTab />
  </TabsContent>
</Tabs>
```

### **3. 빈 상태 (Empty State)**
```tsx
// 찜한 주제가 없을 때
<div className="flex flex-col items-center justify-center py-12">
  <Star className="w-12 h-12 text-muted-foreground mb-4" />
  <p className="text-muted-foreground mb-2">찜한 주제가 없습니다</p>
  <p className="text-sm text-muted-foreground/60">
    주제 탐색에서 마음에 드는 주제를 찜해보세요
  </p>
  <Button asChild variant="outline" className="mt-4">
    <Link to="/explore">주제 탐색하기</Link>
  </Button>
</div>
```

---

## 🔄 라우팅 변경

### **App.tsx 수정안**

```tsx
function App() {
  return (
    <RootLayout>
      <Routes>
        {/* Public */}
        <Route index element={<LoginPage />} />
        
        {/* Protected */}
        <Route path="onboarding" element={
          <ProtectedRoute>
            <OnboardingPage />  {/* 2단계로 확장 */}
          </ProtectedRoute>
        } />
        
        <Route path="explore" element={  {/* dashboard → explore 이름 변경 */}
          <ProtectedRoute>
            <ExplorePage />  {/* 주제 탐색 */}
          </ProtectedRoute>
        } />
        
        <Route path="script" element={
          <ProtectedRoute>
            <ScriptPage />  {/* 탭 구조로 재구성 */}
          </ProtectedRoute>
        } />
        
        <Route path="script/:id" element={  {/* 스크립트 상세 */}
          <ProtectedRoute>
            <ScriptDetailPage />
          </ProtectedRoute>
        } />
        
        <Route path="analysis" element={
          <ProtectedRoute>
            <AnalysisPage />  {/* 2-Tab: 내 채널 + 경쟁 채널 */}
          </ProtectedRoute>
        } />
        
        <Route path="thumbnail" element={
          <ProtectedRoute>
            <ThumbnailPage />
          </ProtectedRoute>
        } />
      </Routes>
    </RootLayout>
  )
}
```

---

## 📊 사용자 플로우 (User Journey)

### **신규 사용자**
```
1. Login (Google OAuth)
   ↓
2. Onboarding Step 1: 정보 수집
   - 카테고리, 업로드 주기, 타겟 청중, 목표
   ↓
3. Onboarding Step 2: 채널 분석
   - AI가 자동 분석 (5-10초)
   - 결과 확인
   ↓
4. Explore (주제 탐색)
   - AI 추천 주제 확인
   - 마음에 드는 주제 찜하기 ⭐
   ↓
5-A. Script (찜한 주제로 작성)
   - 찜한 주제 선택
   - 스크립트 생성
   ↓
5-B. Analysis (경쟁 채널 추가)
   - 경쟁 채널 검색
   - 추가 (최대 3개)
   - 분석 결과 확인
   ↓
6. Thumbnail (썸네일 생성)
   - 스크립트 선택
   - 썸네일 생성
```

### **재방문 사용자**
```
1. Login
   ↓
2. Explore (주제 탐색)
   - 새로운 추천 주제 확인
   - 실시간 트렌드 확인
   ↓
3. Script (이전 스크립트 탭)
   - 작성 중인 스크립트 계속 작성
   - 또는 새 스크립트 작성
   ↓
4. Analysis (내 채널 탭)
   - 최근 영상 성과 확인
   - AI 인사이트 확인
```

---

## 🎯 개발 우선순위

### **Phase 1: 핵심 기능 (필수)** 🔴
1. ✅ **찜하기 기능**
   - DB 스키마 추가
   - API 엔드포인트 (/api/topics/bookmark)
   - UI 버튼 추가

2. ✅ **채널 분석 탭 분리**
   - Analysis Page를 2-Tab으로 재구성
   - 내 채널 탭 추가

3. ✅ **스크립트 탭 분리**
   - Script Page를 2-Tab으로 재구성
   - 이전 스크립트 목록 API

---

### **Phase 2: 개선 기능 (중요)** 🟡
4. ⏸️ **온보딩 확장**
   - Step 2 추가 (채널 분석 결과)
   - 추가 정보 수집 (업로드 주기, 타겟 청중)

5. ⏸️ **내 채널 상세 분석**
   - YouTube Analytics API 연동
   - 구독자 인구통계
   - 최근 영상 성과

6. ⏸️ **찜한 주제로 스크립트 작성**
   - 드롭다운 선택 UI
   - 선택 시 자동 입력

---

### **Phase 3: 부가 기능 (선택)** 🟢
7. ⏸️ **경쟁 채널 추천**
   - 유사 채널 자동 추천
   - 추천 근거 표시

8. ⏸️ **스크립트 재편집**
   - 기존 스크립트 불러오기
   - 수정 후 재저장

9. ⏸️ **트렌드 섹션 강화**
   - 급상승 키워드
   - 커뮤니티 반응

---

## 🛠️ 기술적 구현 방안

### **1. 찜하기 기능**

**Backend:**
```python
# app/models/bookmarked_topic.py (NEW)
class BookmarkedTopic(Base):
    __tablename__ = "bookmarked_topics"
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    topic_id = Column(UUID, ForeignKey("content_topics.id"))
    created_at = Column(DateTime)

# app/api/routes/topics.py (NEW)
@router.post("/bookmarks")
async def bookmark_topic(topic_id: UUID, user: User):
    # 북마크 추가
    
@router.get("/bookmarks")
async def get_bookmarked_topics(user: User):
    # 찜한 주제 목록
```

**Frontend:**
```typescript
// lib/api/services/topics.service.ts (NEW)
export const topicsService = {
  bookmark: (topicId: string) => 
    api.post('/api/topics/bookmarks', { topic_id: topicId }),
    
  getBookmarked: () => 
    api.get('/api/topics/bookmarks'),
}
```

---

### **2. 탭 구조 구현**

**Script Page 예시:**
```tsx
// pages/script/page.tsx
export default function ScriptPage() {
  const [activeTab, setActiveTab] = useState<"create" | "history">("create")
  
  return (
    <div className="flex h-screen">
      <Sidebar />
      
      <main className="flex-1">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="create">새 스크립트 작성</TabsTrigger>
            <TabsTrigger value="history">이전 스크립트</TabsTrigger>
          </TabsList>
          
          <TabsContent value="create">
            <ScriptCreationTab />
          </TabsContent>
          
          <TabsContent value="history">
            <ScriptHistoryTab />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
```

---

### **3. 내 채널 분석 데이터 수집**

**YouTube Analytics API 연동:**
```python
# app/services/youtube_analytics_service.py (NEW)
class YouTubeAnalyticsService:
    async def get_channel_analytics(channel_id: str):
        # YouTube Analytics API 호출
        # - Demographics (연령, 성별, 지역)
        # - Views, Watch time
        # - Traffic sources
        # - Top videos
        
    async def get_video_performance(video_id: str):
        # 특정 영상의 상세 성과
        # - CTR, 평균 시청 시간
        # - 이탈 시점
        # - 구독자 전환율
```

**권한 필요:**
- YouTube Analytics and Reporting API 활성화
- OAuth scope 추가: `youtube.readonly`, `yt-analytics.readonly`

---

## 💾 DB 스키마 추가 필요

### **1. bookmarked_topics 테이블**
```sql
CREATE TABLE bookmarked_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES content_topics(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, topic_id)
);

CREATE INDEX idx_bookmarked_topics_user_id ON bookmarked_topics(user_id);
```

### **2. my_video_analyses 테이블 (이미 있음?)**
```sql
-- 이미 yt_my_video_analysis 테이블이 존재하는지 확인 필요
-- 없으면 생성
```

---

## 📱 반응형 디자인 고려

```tsx
// 데스크탑 (> 1024px)
<div className="grid grid-cols-12 gap-6">
  <aside className="col-span-2">Sidebar</aside>
  <main className="col-span-8">Main Content</main>
  <aside className="col-span-2">Side Panel</aside>
</div>

// 태블릿 (768px ~ 1024px)
<div className="grid grid-cols-12 gap-4">
  <aside className="col-span-3">Sidebar</aside>
  <main className="col-span-9">Main + Side Panel (접을 수 있음)</main>
</div>

// 모바일 (< 768px)
<div className="flex flex-col">
  <nav>Bottom Navigation</nav>
  <main className="flex-1">Full Width</main>
</div>
```

---

## ✅ 체크리스트

### **설계 완료 체크**
- [x] 화면 구조 정의
- [x] 사용자 플로우 설계
- [x] 파일 구조 제안
- [x] API 엔드포인트 정의
- [x] DB 스키마 정의
- [x] UI 컴포넌트 계획

### **개발 전 확인 필요**
- [ ] 찜하기 기능 우선순위 확정
- [ ] YouTube Analytics API 권한 확보
- [ ] DB 마이그레이션 순서
- [ ] 디자인 시스템 컴포넌트 재사용
- [ ] 기존 코드와의 충돌 검토

---

## 🎯 추천 개발 순서

```
Week 1: 찜하기 + 스크립트 탭
  Day 1-2: 찜하기 기능 (Backend + Frontend)
  Day 3-4: 스크립트 2-Tab 구조
  Day 5: 테스트 및 버그 수정

Week 2: 채널 분석 확장
  Day 1-3: 내 채널 탭 (Analytics 연동)
  Day 4-5: 경쟁 채널 탭 개선 (추천 기능)

Week 3: 온보딩 확장
  Day 1-2: 추가 정보 수집
  Day 3-4: 채널 분석 결과 화면
  Day 5: 전체 통합 테스트
```

---

## 💡 핵심 포인트

1. **점진적 개선**: 기존 기능을 유지하면서 확장
2. **탭 구조**: 복잡성을 줄이고 탐색성 향상
3. **찜하기**: 사용자 워크플로우의 핵심 연결고리
4. **내 채널 분석**: 경쟁 채널만큼 중요한 인사이트

---

**이 계획서를 바탕으로 팀과 논의 후 개발 시작하세요!** 🚀

*문서 위치: `/Users/eyegnittab/Desktop/Orbiter/docs/plan/screen-flow-redesign.md`*
