# 🔀 온보딩 플로우 분기 처리 설계

---

## 🎯 분기 조건

**채널 영상 총합 길이 기준:**
- **90분 미만** (신규 크리에이터) → **맞춤 정보 수집 퍼널**
- **90분 이상** (기존 크리에이터) → **채널 분석 결과 퍼널**

---

## 🔄 플로우 다이어그램

```
OAuth 로그인
  ↓
채널 조회 (YouTube API)
  ├─ channel_id 확인
  ├─ 최근 영상 목록 조회
  └─ 총 영상 길이 계산
  ↓
분기 판단
  ├─────────────────────────┬─────────────────────────┐
  │                         │                         │
90분 미만                90분 이상              에러/채널 없음
  │                         │                         │
  ▼                         ▼                         ▼
[맞춤 정보 수집]      [채널 분석 결과]           [맞춤 정보 수집]
  - 카테고리 선택          - 자동 분석 진행          (기본 퍼널)
  - 업로드 주기            - 채널 성격 표시
  - 타겟 청중              - 구독자 특성
  - 목표 설정              - 최근 영상 성과
  ↓                         ↓                         ↓
[탐색 화면]            [탐색 화면]              [탐색 화면]
```

---

## 🗄️ DB 스키마: 온보딩 상태 관리

### **1. user_onboarding_state 테이블 (신규)**

```sql
CREATE TABLE user_onboarding_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- 온보딩 상태
    onboarding_completed BOOLEAN DEFAULT FALSE,
    onboarding_type VARCHAR(50),  -- 'beginner' or 'experienced'
    
    -- 각 단계별 완료 상태
    step_oauth_completed BOOLEAN DEFAULT FALSE,
    step_channel_check_completed BOOLEAN DEFAULT FALSE,
    step_info_collection_completed BOOLEAN DEFAULT FALSE,
    step_analysis_completed BOOLEAN DEFAULT FALSE,
    
    -- 채널 조회 결과
    total_video_duration_minutes INTEGER,  -- 총 영상 길이
    total_video_count INTEGER,             -- 총 영상 수
    channel_check_at TIMESTAMP,            -- 채널 조회 시점
    
    -- 완료 시점
    onboarding_completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_onboarding_user_id ON user_onboarding_state(user_id);
```

---

## 🔧 Backend API 설계

### **1. 채널 조회 및 분기 판단**

```python
# app/api/routes/onboarding.py (NEW)

@router.post("/check-channel")
async def check_channel_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    채널 조회 및 온보딩 타입 결정
    
    Returns:
        {
            "onboarding_type": "beginner" | "experienced",
            "total_duration_minutes": 45,
            "total_video_count": 12,
            "should_analyze": false,
            "next_step": "info_collection" | "channel_analysis"
        }
    """
    # 1. 사용자의 채널 조회
    youtube_channel = await get_user_youtube_channel(db, current_user.id)
    
    if not youtube_channel:
        # 채널 없음 → 기본 퍼널
        return {
            "onboarding_type": "beginner",
            "total_duration_minutes": 0,
            "total_video_count": 0,
            "should_analyze": False,
            "next_step": "info_collection"
        }
    
    # 2. 채널의 모든 영상 조회 (최대 100개)
    videos = await YouTubeService.get_channel_videos(
        channel_id=youtube_channel.channel_id,
        max_results=100
    )
    
    # 3. 총 영상 길이 계산
    total_duration_seconds = 0
    for video in videos:
        duration_str = video.get("duration")  # "PT10M30S" 형식
        duration_seconds = parse_youtube_duration(duration_str)
        total_duration_seconds += duration_seconds
    
    total_duration_minutes = total_duration_seconds // 60
    
    # 4. 분기 판단
    onboarding_type = "experienced" if total_duration_minutes >= 90 else "beginner"
    should_analyze = total_duration_minutes >= 90
    next_step = "channel_analysis" if should_analyze else "info_collection"
    
    # 5. 온보딩 상태 저장
    state = UserOnboardingState(
        user_id=current_user.id,
        onboarding_type=onboarding_type,
        total_video_duration_minutes=total_duration_minutes,
        total_video_count=len(videos),
        step_channel_check_completed=True,
        channel_check_at=datetime.utcnow()
    )
    db.add(state)
    await db.commit()
    
    return {
        "onboarding_type": onboarding_type,
        "total_duration_minutes": total_duration_minutes,
        "total_video_count": len(videos),
        "should_analyze": should_analyze,
        "next_step": next_step
    }


def parse_youtube_duration(duration_str: str) -> int:
    """
    YouTube duration을 초로 변환
    
    PT10M30S → 630초
    PT1H5M → 3900초
    """
    import re
    
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration_str or "")
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds
```

---

### **2. 단계별 완료 API**

```python
@router.post("/complete-step")
async def complete_onboarding_step(
    request: CompleteStepRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    온보딩 단계 완료 처리
    
    Request:
        {
            "step": "info_collection" | "channel_analysis",
            "data": { ... }  # 해당 단계의 데이터
        }
    """
    state = await get_user_onboarding_state(db, current_user.id)
    
    if request.step == "info_collection":
        # 맞춤 정보 저장
        await update_persona(db, current_user.id, request.data)
        state.step_info_collection_completed = True
        
    elif request.step == "channel_analysis":
        # 분석 완료 표시
        state.step_analysis_completed = True
    
    # 모든 필수 단계 완료 시
    if all([
        state.step_channel_check_completed,
        state.step_info_collection_completed or state.step_analysis_completed
    ]):
        state.onboarding_completed = True
        state.onboarding_completed_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "completed": state.onboarding_completed,
        "next_step": "explore" if state.onboarding_completed else None
    }
```

---

## 🎨 Frontend 구현 설계

### **1. Onboarding Router 수정**

```tsx
// pages/onboarding/page.tsx

export default function OnboardingPage() {
  const navigate = useNavigate()
  const [onboardingType, setOnboardingType] = useState<"beginner" | "experienced" | null>(null)
  const [isCheckingChannel, setIsCheckingChannel] = useState(true)
  const [channelInfo, setChannelInfo] = useState(null)
  
  // 페이지 진입 시 채널 조회 및 분기 판단
  useEffect(() => {
    checkChannelAndDecidePath()
  }, [])
  
  const checkChannelAndDecidePath = async () => {
    setIsCheckingChannel(true)
    
    try {
      // API 호출: 채널 조회 및 분기 판단
      const response = await api.post('/api/onboarding/check-channel')
      
      setOnboardingType(response.onboarding_type)
      setChannelInfo({
        totalDuration: response.total_duration_minutes,
        totalVideos: response.total_video_count
      })
      
      // 분기에 따라 state 설정
      if (response.onboarding_type === "beginner") {
        setCurrentStep("info_collection")
      } else {
        setCurrentStep("channel_analysis")
        // 자동으로 채널 분석 시작
        await startChannelAnalysis()
      }
      
    } catch (error) {
      console.error("채널 조회 실패:", error)
      // 에러 시 기본 퍼널 (맞춤 정보 수집)
      setOnboardingType("beginner")
      setCurrentStep("info_collection")
    } finally {
      setIsCheckingChannel(false)
    }
  }
  
  if (isCheckingChannel) {
    return <LoadingScreen message="채널을 확인하고 있습니다..." />
  }
  
  return (
    <div>
      {onboardingType === "beginner" && (
        <InfoCollectionStep 
          onComplete={() => completeOnboarding("info_collection")}
        />
      )}
      
      {onboardingType === "experienced" && (
        <ChannelAnalysisStep 
          channelInfo={channelInfo}
          onComplete={() => completeOnboarding("channel_analysis")}
        />
      )}
    </div>
  )
  
  const completeOnboarding = async (step: string) => {
    await api.post('/api/onboarding/complete-step', { step })
    navigate('/explore')  // 또는 /dashboard
  }
}
```

---

### **2. 맞춤 정보 수집 컴포넌트**

```tsx
// components/info-collection-step.tsx (NEW)

interface InfoCollectionStepProps {
  onComplete: (data: InfoData) => void
}

export function InfoCollectionStep({ onComplete }: InfoCollectionStepProps) {
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [uploadFrequency, setUploadFrequency] = useState<string>("weekly_2_3")
  const [targetAudience, setTargetAudience] = useState({
    age_groups: [],
    interests: ""
  })
  const [goals, setGoals] = useState<string[]>([])
  
  const handleSubmit = () => {
    onComplete({
      categories: selectedCategories,
      upload_frequency: uploadFrequency,
      target_audience: targetAudience,
      goals: goals
    })
  }
  
  return (
    <div className="max-w-2xl mx-auto">
      <h2>맞춤 정보를 입력해주세요</h2>
      
      {/* 카테고리 선택 */}
      <CategorySelector 
        value={selectedCategories}
        onChange={setSelectedCategories}
      />
      
      {/* 업로드 주기 */}
      <FrequencySelector
        value={uploadFrequency}
        onChange={setUploadFrequency}
      />
      
      {/* 타겟 청중 */}
      <AudienceSelector
        value={targetAudience}
        onChange={setTargetAudience}
      />
      
      {/* 목표 설정 */}
      <GoalSelector
        value={goals}
        onChange={setGoals}
      />
      
      <Button onClick={handleSubmit}>다음</Button>
    </div>
  )
}
```

---

### **3. 채널 분석 결과 컴포넌트**

```tsx
// components/channel-analysis-step.tsx (NEW)

interface ChannelAnalysisStepProps {
  channelInfo: {
    totalDuration: number
    totalVideos: number
  }
  onComplete: () => void
}

export function ChannelAnalysisStep({ channelInfo, onComplete }: ChannelAnalysisStepProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(true)
  const [analysis, setAnalysis] = useState(null)
  
  useEffect(() => {
    performAnalysis()
  }, [])
  
  const performAnalysis = async () => {
    setIsAnalyzing(true)
    
    try {
      // 페르소나 생성 (기존 API 활용)
      const persona = await generatePersona()
      setAnalysis(persona)
    } catch (error) {
      console.error("분석 실패:", error)
    } finally {
      setIsAnalyzing(false)
    }
  }
  
  if (isAnalyzing) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <Loader2 className="w-12 h-12 animate-spin text-primary mb-4" />
        <h3 className="text-lg font-semibold mb-2">채널을 분석하고 있습니다</h3>
        <p className="text-sm text-muted-foreground">
          {channelInfo.totalVideos}개 영상을 분석 중입니다... (약 10-20초)
        </p>
      </div>
    )
  }
  
  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">✨ 분석 완료!</h2>
        <p className="text-muted-foreground">
          {channelInfo.totalVideos}개 영상 (총 {channelInfo.totalDuration}분)을 분석했습니다
        </p>
      </div>
      
      {/* 채널 성격 */}
      <Card>
        <CardHeader>
          <CardTitle>📝 내 채널 성격</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-lg">{analysis.channel_personality}</p>
        </CardContent>
      </Card>
      
      {/* 주요 구독자 */}
      <Card>
        <CardHeader>
          <CardTitle>👥 주요 구독자</CardTitle>
        </CardHeader>
        <CardContent>
          <p>{analysis.target_audience}</p>
          <div className="mt-4 flex gap-2">
            {analysis.audience_age_groups.map(age => (
              <Badge key={age}>{age}</Badge>
            ))}
          </div>
        </CardContent>
      </Card>
      
      {/* 콘텐츠 특징 */}
      <Card>
        <CardHeader>
          <CardTitle>💡 콘텐츠 특징</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {analysis.content_features.map((feature, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-primary">•</span>
                <span>{feature}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
      
      <Button onClick={onComplete} className="w-full" size="lg">
        주제 탐색 시작하기
      </Button>
    </div>
  )
}
```

---

## 🎯 각 퍼널별 완료 State 정의

### **State 타입 정의**

```typescript
// types/onboarding.types.ts (NEW)

export type OnboardingType = "beginner" | "experienced"
export type OnboardingStep = 
  | "oauth"
  | "channel_check"
  | "info_collection"
  | "channel_analysis"
  | "completed"

export interface OnboardingState {
  user_id: string
  onboarding_completed: boolean
  onboarding_type: OnboardingType | null
  
  // 단계별 완료 상태
  steps_completed: {
    oauth: boolean
    channel_check: boolean
    info_collection: boolean
    channel_analysis: boolean
  }
  
  // 채널 정보
  channel_info: {
    total_duration_minutes: number
    total_video_count: number
    checked_at: string | null
  }
  
  // 수집된 데이터
  collected_data: {
    categories?: string[]
    upload_frequency?: string
    target_audience?: any
    goals?: string[]
  } | null
  
  // 완료 시점
  completed_at: string | null
}
```

---

### **State 관리 (Context 또는 Zustand)**

```typescript
// store/onboarding.store.ts (NEW)

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface OnboardingStore {
  state: OnboardingState | null
  
  // Actions
  setOnboardingType: (type: OnboardingType) => void
  markStepCompleted: (step: OnboardingStep) => void
  setChannelInfo: (info: any) => void
  setCollectedData: (data: any) => void
  completeOnboarding: () => void
  reset: () => void
}

export const useOnboardingStore = create<OnboardingStore>()(
  persist(
    (set) => ({
      state: null,
      
      setOnboardingType: (type) => set((state) => ({
        state: {
          ...state.state!,
          onboarding_type: type
        }
      })),
      
      markStepCompleted: (step) => set((state) => ({
        state: {
          ...state.state!,
          steps_completed: {
            ...state.state!.steps_completed,
            [step]: true
          }
        }
      })),
      
      completeOnboarding: () => set((state) => ({
        state: {
          ...state.state!,
          onboarding_completed: true,
          completed_at: new Date().toISOString()
        }
      })),
      
      reset: () => set({ state: null })
    }),
    {
      name: 'onboarding-storage',
    }
  )
)
```

---

## 🔄 전체 플로우 코드

### **login/page.tsx 수정**

```typescript
// 기존 코드
try {
  await getMyPersona()
  navigate('/dashboard')
} catch {
  navigate('/onboarding')
}

// 수정 후
try {
  // 1. 온보딩 상태 조회
  const onboardingState = await api.get('/api/onboarding/state')
  
  if (onboardingState.onboarding_completed) {
    // 온보딩 완료 → Dashboard
    navigate('/dashboard')
  } else {
    // 온보딩 미완료 → Onboarding
    navigate('/onboarding')
  }
} catch {
  // 온보딩 상태 없음 → Onboarding (신규 사용자)
  navigate('/onboarding')
}
```

---

### **onboarding/page.tsx 구조**

```tsx
export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState<OnboardingStep>("channel_check")
  const [onboardingType, setOnboardingType] = useState<OnboardingType | null>(null)
  
  useEffect(() => {
    // 채널 조회 및 분기 판단
    checkChannel()
  }, [])
  
  const checkChannel = async () => {
    const result = await api.post('/api/onboarding/check-channel')
    
    setOnboardingType(result.onboarding_type)
    setCurrentStep(result.next_step)
  }
  
  return (
    <div>
      {currentStep === "channel_check" && (
        <LoadingScreen message="채널을 확인하고 있습니다..." />
      )}
      
      {currentStep === "info_collection" && (
        <InfoCollectionStep onComplete={handleInfoComplete} />
      )}
      
      {currentStep === "channel_analysis" && (
        <ChannelAnalysisStep 
          channelInfo={channelInfo}
          onComplete={handleAnalysisComplete}
        />
      )}
    </div>
  )
}
```

---

## 📊 분기 시나리오

### **시나리오 A: 신규 크리에이터 (영상 5개, 총 35분)**

```
1. OAuth 로그인 ✅
   ↓
2. 채널 조회
   - 총 영상 길이: 35분 < 90분
   - 분기 결정: "beginner"
   ↓
3. [맞춤 정보 수집] 화면 표시
   - 카테고리 선택
   - 업로드 주기
   - 타겟 청중
   - 목표
   ↓
4. 정보 저장 후 → [탐색] 화면
```

---

### **시나리오 B: 기존 크리에이터 (영상 50개, 총 180분)**

```
1. OAuth 로그인 ✅
   ↓
2. 채널 조회
   - 총 영상 길이: 180분 ≥ 90분
   - 분기 결정: "experienced"
   ↓
3. [채널 분석 중...] 로딩 표시
   - generatePersona() 자동 호출
   - 10-20초 소요
   ↓
4. [채널 분석 결과] 화면 표시
   - 채널 성격
   - 주요 구독자
   - 콘텐츠 특징
   - 강점/약점
   ↓
5. [주제 탐색 시작하기] 버튼 → [탐색] 화면
```

---

### **시나리오 C: 채널 없음 또는 에러**

```
1. OAuth 로그인 ✅
   ↓
2. 채널 조회
   - 연동된 채널 없음 또는 API 에러
   - 분기 결정: "beginner" (기본값)
   ↓
3. [맞춤 정보 수집] 화면 표시
   (시나리오 A와 동일)
```

---

## 🎯 완료 State 체크 로직

```typescript
// 온보딩 완료 여부 판단
function isOnboardingComplete(state: OnboardingState): boolean {
  const { steps_completed, onboarding_type } = state
  
  // 필수 단계
  const requiredSteps = [
    steps_completed.oauth,
    steps_completed.channel_check
  ]
  
  // 타입별 추가 필수 단계
  if (onboarding_type === "beginner") {
    requiredSteps.push(steps_completed.info_collection)
  } else if (onboarding_type === "experienced") {
    requiredSteps.push(steps_completed.channel_analysis)
  }
  
  // 모든 필수 단계 완료 시 true
  return requiredSteps.every(step => step === true)
}
```

---

## 📋 체크리스트

### **Backend 작업**
- [ ] `user_onboarding_state` 테이블 생성
- [ ] Alembic 마이그레이션 작성
- [ ] `/api/onboarding/check-channel` API 구현
- [ ] `/api/onboarding/complete-step` API 구현
- [ ] `/api/onboarding/state` API 구현
- [ ] YouTube duration 파싱 유틸 함수

### **Frontend 작업**
- [ ] `InfoCollectionStep` 컴포넌트
- [ ] `ChannelAnalysisStep` 컴포넌트
- [ ] `onboarding/page.tsx` 분기 로직
- [ ] `FrequencySelector` 컴포넌트
- [ ] `AudienceSelector` 컴포넌트
- [ ] `GoalSelector` 컴포넌트
- [ ] 온보딩 State 관리 (Zustand or Context)
- [ ] 로딩 화면 개선

### **API 연동**
- [ ] `checkChannel()` 함수
- [ ] `completeStep()` 함수
- [ ] `getOnboardingState()` 함수

---

## ⏱️ 개발 예상 시간

| 작업 | 소요 시간 | 난이도 |
|------|----------|--------|
| DB 스키마 + 마이그레이션 | 1시간 | 쉬움 |
| Backend API (3개) | 2시간 | 보통 |
| Frontend 컴포넌트 (2개) | 3시간 | 보통 |
| 분기 로직 + State 관리 | 2시간 | 보통 |
| 테스트 + 버그 수정 | 2시간 | - |
| **총** | **10시간** | **보통** |

---

## 🚀 단계별 구현 순서

### **Day 1 (4시간)**
1. DB 스키마 + 마이그레이션
2. Backend `/check-channel` API
3. YouTube duration 파싱 함수
4. 기본 테스트

### **Day 2 (4시간)**
1. Backend 완료 (`/complete-step`, `/state`)
2. Frontend 분기 로직 구현
3. 로딩 화면

### **Day 3 (2시간)**
1. `InfoCollectionStep` 컴포넌트
2. 추가 정보 입력 UI

### **Day 4 (2시간)**  
1. `ChannelAnalysisStep` 컴포넌트
2. 분석 결과 표시 UI

### **Day 5 (2시간)**
1. 통합 테스트
2. 버그 수정
3. UX 개선

---

## 💡 핵심 포인트

### **1. 분기 조건은 간단**
```python
if total_duration_minutes >= 90:
    return "experienced"
else:
    return "beginner"
```

### **2. 기존 API 최대 활용**
- ✅ `generatePersona()` - 이미 있음
- ✅ `get_channel_videos()` - 이미 있음
- ✅ `updatePersona()` - 이미 있음

### **3. 점진적 개발 가능**
```
Step 1: 분기 로직만 구현 (기존 화면 재사용)
Step 2: 새로운 화면 추가
Step 3: 추가 정보 수집 강화
```

---

## ⚠️ 주의사항

### **1. YouTube API Quota**
- 영상 100개 조회 시 quota 소모
- 캐싱 전략 필요

### **2. Duration 계산 정확성**
- Shorts 제외 여부?
- Private/Unlisted 영상 처리?

### **3. 에러 처리**
- 채널 조회 실패 → 기본 퍼널로
- 분석 실패 → 맞춤 정보 수집으로

---

## 🎯 결론

**복잡도:** 보통 (10시간)  
**리스크:** 낮음 (기존 API 활용)  
**가치:** 높음 (UX 개선 + 개인화)

**권장 접근:**
1. 먼저 분기 로직만 구현 (2시간)
2. 기존 화면 재사용 테스트
3. 점진적으로 새 화면 추가

---

**충분히 구현 가능한 계획입니다!** 🚀

*문서 위치: `/Users/eyegnittab/Desktop/Orbiter/docs/plan/onboarding-flow-branching.md`*
