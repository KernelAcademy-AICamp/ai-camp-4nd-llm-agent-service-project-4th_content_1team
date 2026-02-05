# 프론트엔드 변경 사항 분석

## 개요

이 문서는 `page.tsx`와 `competitor-analysis.tsx` 파일의 변경 사항을 상세히 설명합니다.

---

## 1. page.tsx 변경 사항

### 파일 경로
`FE/src/pages/script/page.tsx`

### 변경 요약
| 구분 | Main 버전 | 수정 버전 |
|------|-----------|-----------|
| 줄 수 | 46줄 | 92줄 |
| 역할 | UI 레이아웃만 | 백엔드 파이프라인 연동 |

---

### 1-1. 새로 추가된 import 

**Main 버전:**
```tsx
import { Suspense } from "react"
```

**수정 버전:**
```tsx
import { Suspense, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { executeScriptGen, pollScriptGenResult } from "../../lib/api/services"
import type { GeneratedScript, ReferenceArticle } from "../../lib/api/services"
```

**왜 바꿨는지:**
- `useState`: 생성 상태, 스크립트 데이터, 참고자료 등 상태 관리
- `useSearchParams`: URL에서 topic 파라미터 추출
- `executeScriptGen`, `pollScriptGenResult`: 백엔드 스크립트 생성 API 호출

---

### 1-2. ScriptPageContent 컴포넌트 추가 (핵심 변경)

**Main 버전:** 없음

**수정 버전:**
```tsx
function ScriptPageContent() {
  const [searchParams] = useSearchParams()
  const topic = searchParams.get("topic") || "2026 게임 트렌드 예측"

  const [isGenerating, setIsGenerating] = useState(false)
  const [scriptData, setScriptData] = useState<GeneratedScript | null>(null)
  const [references, setReferences] = useState<ReferenceArticle[]>([])
  const [competitorVideos, setCompetitorVideos] = useState<any[]>([])

  const handleGenerate = async () => {
    setIsGenerating(true)
    try {
      const { task_id } = await executeScriptGen(topic)
      const result = await pollScriptGenResult(task_id, (status) => {
        console.log("[FE] 상태:", status)
      })

      if (result.success && result.script) {
        setScriptData(result.script)
        setReferences(result.references || [])
        setCompetitorVideos(result.competitor_videos || [])
      }
    } catch (error) {
      alert("서버 연결 오류. 백엔드가 실행 중인지 확인해주세요.")
    } finally {
      setIsGenerating(false)
    }
  }
  // ...
}
```

**왜 바꿨는지:**
- **백엔드 파이프라인 연동**: `handleGenerate` 함수가 없으면 재생성 버튼이 작동 안 함
- **상태 관리**: 생성 결과(스크립트, 참고자료, 경쟁영상)를 저장해서 하위 컴포넌트에 전달
- **URL 파라미터 활용**: 대시보드에서 선택한 토픽으로 스크립트 생성

---

### 1-3. 컴포넌트 props 전달

**Main 버전:**
```tsx
<ScriptEditor />
<RelatedResources />
<CompetitorAnalysis />
```

**수정 버전:**
```tsx
<ScriptEditor
  apiData={scriptData}
  isGenerating={isGenerating}
  onRegenerate={handleGenerate}
/>
<RelatedResources apiReferences={references} />
<CompetitorAnalysis topic={topic} apiVideos={competitorVideos} />
```

**왜 바꿨는지:**
- **데이터 흐름**: 백엔드 파이프라인 결과 → page.tsx → 각 컴포넌트
- **재생성 기능**: `onRegenerate` 핸들러로 버튼 클릭 시 파이프라인 재실행
- **로딩 상태**: `isGenerating`으로 생성 중 UI 표시

---

### 1-4. Suspense 구조 변경

**Main 버전:**
```tsx
export default function ScriptPage() {
  return (
    <div>
      <Suspense>
        <ScriptHeader />
      </Suspense>
      ...
    </div>
  )
}
```

**수정 버전:**
```tsx
export default function ScriptPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ScriptPageContent />
    </Suspense>
  )
}
```

**왜 바꿨는지:**
- `useSearchParams` 훅은 Suspense 경계 안에서 사용해야 함
- `ScriptPageContent`를 분리해서 Suspense로 감쌈

---

## 2. competitor-analysis.tsx 변경 사항

### 파일 경로
`FE/src/pages/script/components/competitor-analysis.tsx`

### 변경 요약
| 구분 | Main 버전 | 수정 버전 |
|------|-----------|-----------|
| Props | 없음 | topic, apiVideos 받음 |
| 데이터 소스 | YouTube API만 | YouTube API + 백엔드 파이프라인 |

---

### 2-1. Props 인터페이스 추가

**Main 버전:**
```tsx
export function CompetitorAnalysis() {
```

**수정 버전:**
```tsx
interface CompetitorAnalysisProps {
  topic?: string
  apiVideos?: Array<{
    video_id: string
    title: string
    channel: string
    url: string
    thumbnail?: string
    hook_analysis?: string
    weak_points?: string[]
    strong_points?: string[]
  }>
}

export function CompetitorAnalysis({ topic, apiVideos }: CompetitorAnalysisProps = {}) {
```

**왜 바꿨는지:**
- **백엔드 데이터 수신**: 파이프라인에서 분석한 경쟁 영상 데이터 받기
- **분석 결과 포함**: `hook_analysis`, `weak_points`, `strong_points` 등 분석 정보

---

### 2-2. 백엔드 데이터 변환 로직 추가

**Main 버전:** 없음

**수정 버전:**
```tsx
// API Videos를 UI 형식으로 변환 (백엔드 파이프라인 데이터)
const backendVideos = apiVideos?.map((video) => ({
  id: video.video_id,
  channel: video.channel,
  title: video.title,
  thumbnail: video.thumbnail || '',
  url: video.url,
  views: '-',  // 백엔드 데이터에는 없음
  likes: '-',
  comments: '-',
  hook_analysis: video.hook_analysis,
  weak_points: video.weak_points,
  strong_points: video.strong_points
})) || []

// 우선순위: 백엔드 데이터 > YouTube API 데이터
const competitorVideos = backendVideos.length > 0 ? backendVideos : youtubeVideos
```

**왜 바꿨는지:**
- **듀얼 소스**: 백엔드 파이프라인 결과가 있으면 그거 쓰고, 없으면 YouTube API 직접 호출
- **분석 결과 표시**: 파이프라인에서 생성한 hook 분석, 강점/약점 표시 가능

---

### 2-3. 영상 개수 표시 수정

**Main 버전:**
```tsx
{data && (
  <Badge>{data.total_results}개</Badge>
)}
```

**수정 버전:**
```tsx
const videoCount = competitorVideos.length || data?.total_results || 0

{videoCount > 0 && (
  <Badge>{videoCount}개</Badge>
)}
```

**왜 바꿨는지:**
- 백엔드 데이터 사용 시에도 정확한 영상 개수 표시

---

### 2-4. 코드 포맷팅 변경 (기능 무관)

여러 곳에서 공백/줄바꿈 정리:
```tsx
// Before
const allTopics = topicsData 
  ? [...]

// After  
const allTopics = topicsData
  ? [...]
```

**왜 바꿨는지:**
- Prettier/ESLint 자동 포맷팅 결과
- **기능 변경 없음**, 코드 스타일만 정리

---

## 결론

### 필수 변경 (기능 관련)
1. `page.tsx`: `ScriptPageContent` 추가 및 props 전달 → **재생성 버튼 작동**
2. `competitor-analysis.tsx`: Props 인터페이스 및 백엔드 데이터 처리 → **파이프라인 결과 표시**

### 불필요한 변경 (포맷팅)
- 공백, 줄바꿈 정리 → 기능 영향 없음, 되돌려도 됨

---

## 권장 사항

**선택지 A: 네 버전 유지**
- 백엔드 파이프라인과 완전 연동
- 재생성 버튼 작동
- PR에 포함해서 머지

**선택지 B: Main 버전 유지**
- 프론트엔드 변경 최소화
- 백엔드 파이프라인 결과가 화면에 안 뜸
- 재생성 버튼 작동 안 함
- 추후 별도 PR로 작업
