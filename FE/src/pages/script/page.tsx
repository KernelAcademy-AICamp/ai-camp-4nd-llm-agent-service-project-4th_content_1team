"use client"

import { Suspense, useState, useEffect, useRef } from "react"
import { useSearchParams } from "react-router-dom"
import { DashboardSidebar } from "../dashboard/components/sidebar"
import { ScriptEditor } from "./components/script-editor"
import { RelatedResources } from "./components/related-resources"
import { ScriptHeader } from "./components/script-header"
import { executeScriptGen, pollScriptGenResult, getScriptHistory, getScriptById } from "../../lib/api/services"
import type { GeneratedScript, ReferenceArticle, Citation, RelatedVideo } from "../../lib/api/services"

function ScriptPageContent() {
  const [searchParams, setSearchParams] = useSearchParams()
  const topic = searchParams.get("topic") || "2026 게임 트렌드 예측"
  const topicId = searchParams.get("topicId") || undefined

  const [isGenerating, setIsGenerating] = useState(false)
  const [scriptData, setScriptData] = useState<GeneratedScript | null>(null)
  const [references, setReferences] = useState<ReferenceArticle[]>([])
  const [citations, setCitations] = useState<Citation[]>([])
  const [relatedVideos, setRelatedVideos] = useState<RelatedVideo[]>([])
  const [activeCitationUrl, setActiveCitationUrl] = useState<string | null>(null)

  // 자동 생성 트리거 방지 플래그 (useRef: 동기적 즉시 반영 → StrictMode 중복 방지)
  const autoGenRef = useRef(false)

  const normalizeRelatedVideos = (videos: any): RelatedVideo[] => {
    if (!Array.isArray(videos)) return []
    return videos.map((v) => ({
      ...(v as RelatedVideo),
      search_type: ((v as RelatedVideo).search_type as "relevance" | "popular") || "relevance",
    }))
  }

  // 페이지 로드 시 DB에서 이전 결과 불러오기 → 없으면 자동 생성
  useEffect(() => {
    const loadHistoryOrGenerate = async () => {
      let hasExistingData = false

      try {
        if (topicId) {
          const result = await getScriptById(topicId)
          if (result.script) {
            setScriptData(result.script)
            setReferences(result.references || [])
            setCitations(result.citations || [])
            setRelatedVideos(normalizeRelatedVideos(result.related_videos))
            hasExistingData = true
          }
        } else {
          const history = await getScriptHistory(1)
          if (history.length > 0) {
            const latest = history[0]
            if (latest.script) {
              setScriptData(latest.script)
              setReferences(latest.references || [])
              setCitations(latest.citations || [])
              setRelatedVideos(normalizeRelatedVideos(latest.related_videos))
              hasExistingData = true
            }
          }
        }
      } catch (error) {
        console.log("[FE] 이력 조회 실패 (첫 방문이면 정상):", error)
      }

      // DB에 이전 결과가 없으면 자동으로 스크립트 + 참고자료 생성
      if (!hasExistingData && !autoGenRef.current) {
        console.log("[FE] 이전 결과 없음 → 자동 생성 시작")
        autoGenRef.current = true
        handleGenerate()
      }
    }
    loadHistoryOrGenerate()
  }, [topicId])

  const handleGenerate = async () => {
    setIsGenerating(true)
    try {
      const { task_id } = await executeScriptGen(topic, topicId)
      const result = await pollScriptGenResult(task_id, (status) => {
        console.log("[FE] 상태:", status)
      })
      if (result.success && result.script) {
        setScriptData(result.script)
        setReferences(result.references || [])
        setCitations(result.citations || [])
        setRelatedVideos(normalizeRelatedVideos(result.related_videos))
        if (result.topic_request_id) {
          const newParams = new URLSearchParams(searchParams)
          newParams.set("topicId", result.topic_request_id)
          setSearchParams(newParams, { replace: true })
        }
      } else {
        const errMsg = result.error || result.message || "알 수 없는 오류"
        alert(`생성 실패: ${errMsg}`)
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
              citations={citations}
              onCitationClick={(url) => setActiveCitationUrl(url)}
            />
          </div>

          {/* Right Panel - Resources & Analysis */}
          <div className="w-1/2 overflow-auto">
            <div className="p-6 space-y-6">
              <RelatedResources apiReferences={references} activeCitationUrl={activeCitationUrl} relatedVideos={relatedVideos} />
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
