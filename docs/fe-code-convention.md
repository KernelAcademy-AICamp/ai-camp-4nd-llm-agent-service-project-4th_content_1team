# FE Code Convention

> `FE/src/pages/analysis/page.tsx` 분석 기반 코드 컨벤션

---

## 📁 파일 구조

### 1. Import 순서
```tsx
// 1. React 관련
import { useState, useEffect } from "react"

// 2. 내부 컴포넌트 (상대 경로)
import { DashboardSidebar } from "../dashboard/components/sidebar"
import { Card, CardContent } from "../../components/ui/card"

// 3. 아이콘
import { BarChart3, Users, Search } from "lucide-react"

// 4. 외부 라이브러리
import { useQuery, useMutation } from "@tanstack/react-query"

// 5. API 및 타입 (type keyword 사용)
import {
  searchChannels,
  type ChannelSearchResult,
  type CompetitorChannelResponse,
} from "../../lib/api/index"
```

### 2. 파일 상단 Directive
```tsx
"use client"  // Next.js App Router용 (필요시)
```

---

## 🎯 네이밍 규칙

### 1. 컴포넌트명
```tsx
✅ PascalCase
function VideoAnalysisResults() { }
export default function AnalysisPage() { }

❌ camelCase, kebab-case
function videoAnalysisResults() { }
function analysis-page() { }
```

### 2. 함수명
```tsx
✅ camelCase
function formatNumber(num: number) { }
function getAnalysisButton(video) { }

// 이벤트 핸들러: handle prefix
const handleSearch = () => { }
const handleAddCompetitor = (channel) => { }
```

### 3. 변수/State
```tsx
✅ camelCase
const [searchQuery, setSearchQuery] = useState("")
const [analyzingVideoId, setAnalyzingVideoId] = useState<string | null>(null)

// React Query
const { data: searchResults, isLoading } = useQuery({ })
const { data: competitorList } = useQuery({ })
```

### 4. Props 타입
```tsx
✅ interface 정의 + destructuring
function VideoAnalysisResults({ video }: { video: CompetitorChannelVideo }) {
  return <div>...</div>
}

// 복잡한 경우
interface VideoAnalysisResultsProps {
  video: CompetitorChannelVideo
  onAnalyze?: () => void
}

function VideoAnalysisResults({ video, onAnalyze }: VideoAnalysisResultsProps) {
  return <div>...</div>
}
```

---

## 🎨 스타일링

### 1. TailwindCSS 표준 사용
```tsx
✅ Tailwind 유틸리티 클래스
<div className="flex items-center gap-4 p-3 rounded-lg border">

✅ 조건부 클래스
<Button
  variant={isExpanded ? "default" : "outline"}
  className="w-full mt-2 gap-1 text-xs"
>

❌ 인라인 스타일, 커스텀 폰트
<div style={{ padding: '12px' }}>  // X
<div className="font-['Pretendard',sans-serif]">  // X
```

### 2. 반응형 클래스
```tsx
✅ Tailwind 반응형 prefix
<div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
```

---

## 🧩 컴포넌트 구조

### 1. 서브 컴포넌트 분리
```tsx
// 파일 상단에 서브 컴포넌트 정의
function VideoAnalysisResults({ video }: { video: CompetitorChannelVideo }) {
  return (
    <div className="mt-3 space-y-3">
      {/* ... */}
    </div>
  )
}

// 메인 컴포넌트
export default function AnalysisPage() {
  return (
    <div>
      <VideoAnalysisResults video={video} />
    </div>
  )
}
```

### 2. State 정의
```tsx
// State는 컴포넌트 상단에 모아서 정의
const [searchQuery, setSearchQuery] = useState("")
const [shouldSearch, setShouldSearch] = useState(false)
const [analyzingVideoId, setAnalyzingVideoId] = useState<string | null>(null)
const queryClient = useQueryClient()
```

### 3. React Query
```tsx
// useQuery: 데이터 조회
const { data: searchResults, isLoading, error } = useQuery({
  queryKey: ['channel-search', searchQuery],
  queryFn: () => searchChannels(searchQuery),
  enabled: shouldSearch && !!searchQuery.trim(),
  staleTime: 1000 * 60 * 5,
})

// useMutation: 데이터 변경
const addMutation = useMutation({
  mutationFn: (channel) => addCompetitorChannel(channel),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['competitor-channels'] })
  },
})
```

---

## 🔄 조건부 렌더링

### 1. 간단한 조건
```tsx
✅ && 연산자
{isLoading && <Loader2 />}
{video.analyzed_at && <VideoAnalysisResults />}

✅ 삼항 연산자
{isActive ? "활성" : "비활성"}
<Button variant={isExpanded ? "default" : "outline"}>
```

### 2. 복잡한 조건
```tsx
✅ 조기 리턴 패턴
if (isAnalyzing) {
  return <Button disabled>분석 중...</Button>
}

if (isAnalyzed) {
  return <Button>분석 결과 보기</Button>
}

return <Button>AI 영상 분석</Button>
```

### 3. 빈 상태 처리
```tsx
✅ 명시적 빈 상태 UI
{!competitorList || competitorList.total === 0 ? (
  <div className="flex flex-col items-center py-12">
    <Users className="w-12 h-12 text-muted-foreground" />
    <h3>아직 등록된 경쟁 유튜버가 없습니다</h3>
  </div>
) : (
  <div>{/* 목록 */}</div>
)}
```

---

## 📝 주석

### 1. 섹션 주석
```tsx
{/* Header */}
<div>...</div>

{/* 채널 검색 쿼리 */}
const { data } = useQuery({ })

{/* 등록된 경쟁 채널 목록 */}
const { data: competitorList } = useQuery({ })
```

### 2. 설명 주석
```tsx
// 페이지 진입 시 최신 영상 자동 갱신 (분석 중이 아닐 때만 invalidate)
useEffect(() => {
  refreshMutation.mutate()
}, [])

// invalidateQueries 대신 캐시 직접 업데이트 → 스크롤 위치 유지
queryClient.setQueryData(['competitor-channels'], (old) => { })
```

---

## 🎭 이벤트 핸들러

### 1. 네이밍
```tsx
✅ handle prefix
const handleSearch = () => { }
const handleAddCompetitor = (channel) => { }
const handleAnalyzeVideo = (video, e) => { }
```

### 2. 이벤트 전파 제어
```tsx
const handleAnalyzeVideo = (video: CompetitorChannelVideo, e: React.MouseEvent) => {
  e.preventDefault()
  e.stopPropagation()
  
  // 로직
}
```

---

## 🧮 유틸리티 함수

### 1. 컴포넌트 내부 정의
```tsx
export default function AnalysisPage() {
  // Helper 함수
  function formatNumber(num: number): string {
    if (num >= 10000) {
      return `${(num / 10000).toFixed(1)}만`
    }
    return num.toLocaleString()
  }

  const getAnalysisButton = (video: CompetitorChannelVideo) => {
    // 조건에 따라 다른 Button 반환
  }
  
  return <div>...</div>
}
```

---

## 🏗️ 레이아웃 구조

### 1. 페이지 레이아웃
```tsx
return (
  <div className="min-h-screen bg-background flex">
    <DashboardSidebar />
    
    <main className="flex-1 p-6 overflow-auto">
      <div className="max-w-[1400px] mx-auto space-y-6">
        {/* 컨텐츠 */}
      </div>
    </main>
  </div>
)
```

### 2. Card 기반 섹션
```tsx
<Card className="border-border/50 bg-card/50 backdrop-blur">
  <CardHeader>
    <CardTitle className="text-lg">제목</CardTitle>
  </CardHeader>
  <CardContent>
    {/* 내용 */}
  </CardContent>
</Card>
```

---

## 🔍 타입 안전성

### 1. 타입 정의
```tsx
✅ type import 사용
import { type ChannelSearchResult } from "../../lib/api/index"

✅ 제네릭 타입
const [analyzingVideoId, setAnalyzingVideoId] = useState<string | null>(null)

✅ 함수 반환 타입
function formatNumber(num: number): string { }
```

### 2. 타입 단언 (최소화)
```tsx
// 필요한 경우에만 사용
const error = (listError as any)?.response?.data?.detail
```

---

## ✅ 체크리스트

### 코드 작성 시 확인사항

- [ ] Import 순서 준수 (React → 컴포넌트 → 아이콘 → 라이브러리 → API/타입)
- [ ] 컴포넌트명 PascalCase
- [ ] 함수/변수명 camelCase
- [ ] 이벤트 핸들러 `handle` prefix
- [ ] Props 타입 정의 + destructuring
- [ ] TailwindCSS 표준 클래스 사용
- [ ] 조건부 렌더링 간단하게 (&&, ?:)
- [ ] 주석 적절히 사용 (섹션, 설명)
- [ ] 타입 안전성 확보
- [ ] 빈 상태 UI 처리

---

## 🚫 안티패턴

```tsx
❌ 인라인 하드코딩
<div>구독자 10000</div>

✅ 함수로 추출
<div>구독자 {formatNumber(subscriber)}</div>

---

❌ 복잡한 중첩 조건
{isA && (isB ? (isC ? <A /> : <B />) : <C />)}

✅ 조기 리턴 패턴 또는 서브 컴포넌트
function MyComponent() {
  if (isA && isB && isC) return <A />
  if (isA && isB) return <B />
  if (isA) return <C />
  return null
}

---

❌ 타입 없는 함수
const handleClick = (data) => { }

✅ 타입 명시
const handleClick = (data: ChannelData) => { }

---

❌ 커스텀 폰트 직접 지정
className="font-['Pretendard',sans-serif]"

✅ Tailwind 표준
className="font-medium"
```

---

## 📚 참고

- **기존 컨벤션**: `docs/app-sidebar-refactoring-review.md`
- **UI 컴포넌트**: `shadcn/ui` 기반
- **아이콘**: `lucide-react`
- **스타일링**: `TailwindCSS`
- **상태 관리**: `@tanstack/react-query`
