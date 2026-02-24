"use client"

import { Suspense, useState, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import { DashboardSidebar } from "../dashboard/components/sidebar"
import { ScriptEditor } from "./components/script-editor"
import { RelatedResources } from "./components/related-resources"
import { ScriptHeader } from "./components/script-header"
import { runResearchOnly, executeScriptGen, pollScriptGenResult, getScriptHistory, getScriptById } from "../../lib/api/services"
import type { GeneratedScript, ReferenceArticle, Citation, YoutubeVideo } from "../../lib/api/services"

function ScriptPageContent() {
  const [searchParams, setSearchParams] = useSearchParams()
  const topic = searchParams.get("topic") || "2026 게임 트렌드 예측"
  const topicId = searchParams.get("topicId") || undefined

  const [isGenerating, setIsGenerating] = useState(false)
  const [scriptData, setScriptData] = useState<GeneratedScript | null>(null)
  const [references, setReferences] = useState<ReferenceArticle[]>([])
  const [citations, setCitations] = useState<Citation[]>([])
  const [youtubeVideos, setYoutubeVideos] = useState<YoutubeVideo[]>([])
  const [activeCitationUrl, setActiveCitationUrl] = useState<string | null>(null)

  // 자동 생성 트리거 방지 플래그
  const [autoGenTriggered, setAutoGenTriggered] = useState(false)

  // 페이지 로드 시 DB에서 이전 결과 불러오기 → 없으면 자동 생성
  useEffect(() => {
    const loadHistoryOrGenerate = async () => {
      let hasExistingData = false

      try {
        if (topicId) {
          // topicId가 있으면 해당 결과만 조회
          const result = await getScriptById(topicId)
          if (result.script) {
            console.log("[FE] 이전 결과 복원 (by ID):", result.topic_title)
            setScriptData(result.script)
            setReferences(result.references || [])
            setCitations(result.citations || [])
            hasExistingData = true
          }
        } else {
          // topicId 없으면 최근 이력에서 복원
          const history = await getScriptHistory(1)
          if (history.length > 0) {
            const latest = history[0]
            if (latest.script) {
              console.log("[FE] 이전 결과 복원 (최근):", latest.topic_title)
              setScriptData(latest.script)
              setReferences(latest.references || [])
              setCitations(latest.citations || [])
              hasExistingData = true
            }
          }
        }
      } catch (error) {
        console.log("[FE] 이력 조회 실패 (첫 방문이면 정상):", error)
      }

      // DB에 이전 결과가 없으면 자동으로 스크립트 + 참고자료 생성
      if (!hasExistingData && !autoGenTriggered) {
        console.log("[FE] 이전 결과 없음 → 자동 생성 시작")
        setAutoGenTriggered(true)
        handleGenerate()
      }
    }
    loadHistoryOrGenerate()
  }, [topicId])

  const handleGenerate = async () => {
    // -----------------------------------------------------------------------
    // [TEST] Intent Analyzer → Planner → News Research 순서 실행
    // 각 키워드당 1개 기사를 선별하여 참고자료 패널에 표시합니다.
    // -----------------------------------------------------------------------
    setIsGenerating(true)
    try {
      console.log("[FE][TEST] Intent → Planner → Research 실행 요청:", topic)
      const result = await runResearchOnly(topic, topicId)

      // 참고자료 표시
      if (result.references && result.references.length > 0) {
        setReferences(result.references)
        console.log(`[FE][TEST] 참고자료 ${result.references.length}개 수집 완료`)
      }

      // YouTube 영상 표시
      if (result.youtube_videos && result.youtube_videos.length > 0) {
        setYoutubeVideos(result.youtube_videos)
        console.log(`[FE][TEST] YouTube 영상 ${result.youtube_videos.length}개 수집 완료`)
      }

      // Planner 결과 콘솔 출력
      if (result.content_brief) {
        const { content_angle, research_plan } = result.content_brief
        console.group("[FE][TEST] Planner 결과 (content_brief)")

        console.group("콘텐츠 앵글")
        console.log("앵글:  ", content_angle.angle)
        console.log("설명:  ", content_angle.description)
        console.log("훅:    ", content_angle.hook)
        console.groupEnd()

        console.group(`리서치 플랜 (${research_plan.sources.length}개 소스)`)
        research_plan.sources.forEach((s, i) => {
          console.log(`  ${i + 1}. "${s.keyword}"`)
          console.log(`     활용: ${s.how_to_use}`)
        })
        console.log("유튜브 검색 키워드:", research_plan.youtube_keywords)
        console.groupEnd()

        console.log("--- 전체 JSON ---")
        console.log(JSON.stringify(result.content_brief, null, 2))
        console.groupEnd()
      } else {
        console.warn("[FE][TEST] content_brief 없음:", result)
      }

      alert(`[TEST] Research 완료! 참고자료 ${result.references?.length || 0}개 수집. 브라우저 콘솔(F12)에서 Planner 결과를 확인하세요.`)
    } catch (error) {
      console.error("[FE][TEST] API 오류:", error)
      alert("서버 연결 오류. 백엔드가 실행 중인지 확인해주세요.")
    } finally {
      setIsGenerating(false)
    }
    // -----------------------------------------------------------------------
    // [ORIGINAL] 아래는 원래 풀 파이프라인 코드 (테스트 후 복원)
    // -----------------------------------------------------------------------
    // setIsGenerating(true)
    // try {
    //   const { task_id } = await executeScriptGen(topic, topicId)
    //   const result = await pollScriptGenResult(task_id, (status) => {
    //     console.log("[FE] 상태:", status)
    //   })
    //   if (result.success && result.script) {
    //     setScriptData(result.script)
    //     setReferences(result.references || [])
    //     setCitations(result.citations || [])
    //     if (result.topic_request_id) {
    //       const newParams = new URLSearchParams(searchParams)
    //       newParams.set("topicId", result.topic_request_id)
    //       setSearchParams(newParams, { replace: true })
    //     }
    //   } else {
    //     alert(`생성 실패: ${result.error}`)
    //   }
    // } catch (error) {
    //   alert("서버 연결 오류. 백엔드가 실행 중인지 확인해주세요.")
    // } finally {
    //   setIsGenerating(false)
    // }
  }

  return (
    <div className="min-h-screen bg-background flex">
      <DashboardSidebar />

      <main className="flex-1 flex flex-col overflow-hidden">
        <Suspense fallback={<ScriptHeaderSkeleton />}>
          <ScriptHeader />
        </Suspense>

        <div className="flex-1 flex overflow-hidden">
          {/* Left Panel - Script Editor */}
          <div className="w-1/2 border-r border-border overflow-auto p-6">
            <ScriptEditor
              apiData={scriptData}
              isGenerating={isGenerating}
              onRegenerate={handleGenerate}
              citations={citations}
              onCitationClick={(url) => setActiveCitationUrl(url)}
            />
          </div>

          {/* Right Panel - Resources & Analysis */}
          <div className="w-1/2 overflow-auto">
            <div className="p-6 space-y-6">
              <RelatedResources apiReferences={references} youtubeVideos={youtubeVideos} activeCitationUrl={activeCitationUrl} />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default function ScriptPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>
      <ScriptPageContent />
    </Suspense>
  )
}

function ScriptHeaderSkeleton() {
  return (
    <div className="border-b border-border p-4">
      <div className="h-8 w-64 bg-muted animate-pulse rounded" />
    </div>
  )
}
