"use client"

import { Suspense, useState, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import { DashboardSidebar } from "../dashboard/components/sidebar"
import { ScriptEditor } from "./components/script-editor"
import { RelatedResources } from "./components/related-resources"
import { CompetitorAnalysis } from "./components/competitor-analysis"
import { ScriptHeader } from "./components/script-header"
import { executeScriptGen, pollScriptGenResult, getScriptHistory } from "../../lib/api/services"
import type { GeneratedScript, ReferenceArticle } from "../../lib/api/services"

function ScriptPageContent() {
  const [searchParams] = useSearchParams()
  const topic = searchParams.get("topic") || "2026 게임 트렌드 예측"
  const topicId = searchParams.get("topicId") || undefined

  const [isGenerating, setIsGenerating] = useState(false)
  const [scriptData, setScriptData] = useState<GeneratedScript | null>(null)
  const [references, setReferences] = useState<ReferenceArticle[]>([])
  const [competitorVideos, setCompetitorVideos] = useState<any[]>([])

  // 페이지 로드 시 DB에서 이전 결과 불러오기
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const history = await getScriptHistory(1)
        if (history.length > 0) {
          const latest = history[0]
          if (latest.script) {
            console.log("[FE] 이전 결과 복원:", latest.topic_title)
            setScriptData(latest.script)
            setReferences(latest.references || [])
            setCompetitorVideos(latest.competitor_videos || [])
          }
        }
      } catch (error) {
        console.log("[FE] 이력 조회 실패 (첫 방문이면 정상):", error)
      }
    }
    loadHistory()
  }, [])

  const handleGenerate = async () => {
    setIsGenerating(true)
    try {
      console.log("[FE] 스크립트 생성 요청:", topic)
      const { task_id } = await executeScriptGen(topic, topicId)
      console.log("[FE] Task ID:", task_id)

      const result = await pollScriptGenResult(task_id, (status) => {
        console.log("[FE] 상태:", status)
      })

      if (result.success && result.script) {
        console.log("[FE] 생성 완료!", result)
        setScriptData(result.script)
        setReferences(result.references || [])
        setCompetitorVideos(result.competitor_videos || [])
      } else {
        console.error("[FE] 생성 실패:", result.error)
        alert(`생성 실패: ${result.error}`)
      }
    } catch (error) {
      console.error("[FE] API 오류:", error)
      alert("서버 연결 오류. 백엔드가 실행 중인지 확인해주세요.")
    } finally {
      setIsGenerating(false)
    }
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
            />
          </div>

          {/* Right Panel - Resources & Analysis */}
          <div className="w-1/2 overflow-auto">
            <div className="p-6 space-y-6">
              <RelatedResources apiReferences={references} />
              <CompetitorAnalysis />
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
