"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Loader2 } from "lucide-react"

// API
import { generatePersona, generateManualPersona, getMyPersona } from "../../lib/api/services"
import { getChannelStatus } from "../../lib/api/services"
import { generateTrendTopics, getTopics } from "../../lib/api/services"
import type { PersonaResponse, ManualPersonaRequest, TopicResponse } from "../../lib/api/types"

// 컴포넌트
import { StepIndicator } from "./components/step-indicator"
import { LoadingChannelAnalysis } from "./components/loading-channel-analysis"
import { ChannelAnalysisResult, type AnalysisResultData, type TrendPreviewItem } from "./components/channel-analysis-result"
import { StepCategorySelect } from "./components/step-category-select"
import { StepTargetAudience, type Gender } from "./components/step-target-audience"
import { StepBenchmarkChannels, type BenchmarkChannel } from "./components/step-benchmark-channels"
import { StepChannelConcept } from "./components/step-channel-concept"
import { LoadingTrendRecommendation } from "./components/loading-trend-recommendation"

// ─── 상태머신 Phase 타입 ─────────────────────────────────────
type OnboardingPhase =
  | "checking"                // 공통: 채널 상태 확인 중
  | "loading-analysis"        // Branch A: 채널 분석 로딩
  | "analysis-result"         // Branch A: 분석 결과 화면
  | "step-category"           // Branch B: 1단계
  | "step-audience"           // Branch B: 2단계
  | "step-benchmark"          // Branch B: 3단계
  | "step-concept"            // Branch B: 4단계
  | "loading-recommendation"  // Branch B: 트렌드 추천 로딩

// ─── Branch B 입력값 누적 타입 ───────────────────────────────
interface ManualInputData {
  categories: string[]
  gender: Gender
  ageGroup: number
  benchmarkChannels: BenchmarkChannel[]
  topicKeywords: string[]
  styleKeywords: string[]
}

// ─── 메인 컴포넌트 ──────────────────────────────────────────
export default function OnboardingPage() {
  const navigate = useNavigate()

  // 상태머신
  const [phase, setPhase] = useState<OnboardingPhase>("checking")
  const [error, setError] = useState<string | null>(null)

  // Branch A: 페르소나 데이터 (결과 화면에서 사용)
  const [persona, setPersona] = useState<PersonaResponse | null>(null)
  const [trendPreviews, setTrendPreviews] = useState<TrendPreviewItem[]>([])

  // Branch B: 4단계 입력값 누적
  const [manualInput, setManualInput] = useState<Partial<ManualInputData>>({})

  // API 진행 단계 (0=시작전, 1=첫번째API중, 2=첫번째완료+두번째중, 3=전부완료)
  const [apiStep, setApiStep] = useState(0)

  // API 완료 / 애니메이션 완료 동기화
  const apiDoneRef = useRef(false)
  const animDoneRef = useRef(false)
  const nextPhaseRef = useRef<OnboardingPhase | "navigate-explore">("checking")

  // StrictMode 중복 호출 방지
  const hasCalledRef = useRef(false)

  // ─── 공통: 진입 시 채널 상태 확인 ──────────────────────
  useEffect(() => {
    if (hasCalledRef.current) return
    hasCalledRef.current = true

    const checkStatus = async () => {
      try {
        const status = await getChannelStatus()

        if (status.has_enough_videos) {
          // Branch A: 자동 분석
          setPhase("loading-analysis")
        } else {
          // Branch B: 수동 4단계
          setPhase("step-category")
        }
      } catch (err: any) {
        console.error("채널 상태 확인 실패:", err)
        // 실패 시 Branch B로 fallback
        setPhase("step-category")
      }
    }

    checkStatus()
  }, [])

  // ─── Branch A: 분석 로딩 phase 진입 시 API 호출 ────────
  useEffect(() => {
    if (phase !== "loading-analysis") return

    apiDoneRef.current = false
    animDoneRef.current = false
    nextPhaseRef.current = "analysis-result"
    setApiStep(0)

    const runAnalysis = async () => {
      try {
        // 1. 페르소나 생성
        setApiStep(1)
        await generatePersona()
        setApiStep(2)

        // 2. 트렌드 추천 생성
        await generateTrendTopics()
        setApiStep(3)
      } catch (err: any) {
        console.error("Branch A 분석 실패:", err)
        setError(err.response?.data?.detail || "채널 분석 중 오류가 발생했습니다.")
      } finally {
        setApiStep(3)
        apiDoneRef.current = true
        if (animDoneRef.current) {
          setPhase("analysis-result")
        }
      }
    }

    runAnalysis()
  }, [phase])

  // ─── Branch B: 추천 로딩 phase 진입 시 API 호출 ────────
  useEffect(() => {
    if (phase !== "loading-recommendation") return

    apiDoneRef.current = false
    animDoneRef.current = false
    nextPhaseRef.current = "navigate-explore"
    setApiStep(0)

    const runManual = async () => {
      try {
        const input = manualInput as ManualInputData

        // 연령대 → BE 포맷 변환 (10 → "10-19", 50 → "50+")
        const ageGroupStr = input.ageGroup >= 50
          ? "50+"
          : `${input.ageGroup}-${input.ageGroup + 9}`

        // 1. 수동 페르소나 생성
        setApiStep(1)
        const request: ManualPersonaRequest = {
          categories: input.categories,
          gender: input.gender,
          age_group: ageGroupStr,
          topic_keywords: input.topicKeywords,
          style_keywords: input.styleKeywords,
          benchmark_channel_ids: input.benchmarkChannels.map((ch) => ch.channelId),
        }

        await generateManualPersona(request)
        setApiStep(2)

        // 2. 트렌드 추천 생성
        await generateTrendTopics()
        setApiStep(3)
      } catch (err: any) {
        console.error("Branch B 처리 실패:", err)
        // 실패해도 explore로 이동 (빈 상태 표시)
      } finally {
        setApiStep(3)
        apiDoneRef.current = true
        if (animDoneRef.current) {
          navigate("/explore")
        }
      }
    }

    runManual()
  }, [phase, manualInput, navigate])

  // ─── Branch A: 결과 화면 진입 시 DB에서 페르소나 + 추천 조회 ───
  useEffect(() => {
    if (phase !== "analysis-result") return

    const fetchData = async () => {
      try {
        const [personaData, topicsData] = await Promise.all([
          getMyPersona(),
          getTopics(),
        ])
        setPersona(personaData)

        // 추천 타입별 대표 1개씩 추출
        const typeOrder: TrendPreviewItem["type"][] = ["hit_pattern", "viewer_needs", "trend_driven"]
        const previews: TrendPreviewItem[] = []
        for (const type of typeOrder) {
          const topic = topicsData.trend_topics.find(
            (t: TopicResponse) => t.recommendation_type === type
          )
          if (topic) {
            previews.push({
              type,
              topicTitle: topic.title,
              reason: topic.recommendation_reason || "",
            })
          }
        }
        setTrendPreviews(previews)
      } catch (err) {
        console.error("결과 데이터 조회 실패:", err)
      }
    }

    fetchData()
  }, [phase])

  // ─── 로딩 애니메이션 완료 콜백 ─────────────────────────
  const handleLoadingComplete = useCallback(() => {
    animDoneRef.current = true
    if (apiDoneRef.current) {
      if (nextPhaseRef.current === "navigate-explore") {
        navigate("/explore")
      } else {
        setPhase(nextPhaseRef.current)
      }
    }
    // API 아직 안 끝났으면 API 완료 시 전환됨
  }, [navigate])

  // ─── Branch A: 결과 화면 → explore ────────────────────
  const handleAnalysisResultComplete = () => {
    navigate("/explore")
  }

  // ─── Branch B: 4단계 핸들러 ────────────────────────────
  const handleCategoryNext = (categories: string[]) => {
    setManualInput((prev) => ({ ...prev, categories }))
    setPhase("step-audience")
  }

  const handleAudienceNext = (data: { gender: Gender; ageGroup: number }) => {
    setManualInput((prev) => ({ ...prev, gender: data.gender, ageGroup: data.ageGroup }))
    setPhase("step-benchmark")
  }

  const handleBenchmarkNext = (channels: BenchmarkChannel[]) => {
    setManualInput((prev) => ({ ...prev, benchmarkChannels: channels }))
    setPhase("step-concept")
  }

  const handleBenchmarkSkip = () => {
    setManualInput((prev) => ({ ...prev, benchmarkChannels: [] }))
    setPhase("step-concept")
  }

  const handleConceptNext = (data: { topicKeywords: string[]; styleKeywords: string[] }) => {
    setManualInput((prev) => ({
      ...prev,
      topicKeywords: data.topicKeywords,
      styleKeywords: data.styleKeywords,
    }))
    setPhase("loading-recommendation")
  }

  // ─── Branch B: 이전 버튼 핸들러 ───────────────────────
  const handleAudiencePrev = () => setPhase("step-category")
  const handleBenchmarkPrev = () => setPhase("step-audience")
  const handleConceptPrev = () => setPhase("step-benchmark")

  // ─── 분석 결과 데이터 변환 (Branch A) ──────────────────
  const buildAnalysisData = (): AnalysisResultData => {
    if (!persona) {
      return {
        channelName: "내 채널",
        mainTopics: [],
        contentStyle: "",
        toneSamples: [],
        toneManner: "",
        successFormula: "",
        hitPatterns: [],
        videoTypes: {},
        contentStructures: {},
        trendPreviews: [],
      }
    }
    return {
      channelName: persona.one_liner || "내 채널",
      mainTopics: persona.main_topics || [],
      contentStyle: persona.content_style || "",
      toneSamples: persona.tone_samples || [],
      toneManner: persona.tone_manner || "",
      successFormula: persona.success_formula || "",
      hitPatterns: persona.hit_patterns || [],
      videoTypes: persona.video_types || {},
      contentStructures: persona.content_structures || {},
      trendPreviews,
    }
  }

  // ─── Branch B: 현재 스텝 번호 (StepIndicator용) ───────
  const getManualStep = (): number => {
    switch (phase) {
      case "step-category": return 1
      case "step-audience": return 2
      case "step-benchmark": return 3
      case "step-concept": return 4
      default: return 0
    }
  }

  const isManualStep = phase.startsWith("step-")

  // ─── 렌더링 ───────────────────────────────────────────
  return (
    <div className="min-h-screen bg-background">
      {/* checking: 채널 상태 확인 중 */}
      {phase === "checking" && (
        <div className="min-h-screen flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-10 h-10 text-primary animate-spin" />
            <p className="text-sm text-muted-foreground">채널 정보를 확인하고 있어요...</p>
          </div>
        </div>
      )}

      {/* Branch A: 채널 분석 로딩 */}
      {phase === "loading-analysis" && (
        <LoadingChannelAnalysis
          onComplete={handleLoadingComplete}
          hasCompetitors={false}
          apiStep={apiStep}
        />
      )}

      {/* Branch A: 분석 결과 화면 */}
      {phase === "analysis-result" && (
        <ChannelAnalysisResult
          onComplete={handleAnalysisResultComplete}
          hasCompetitors={false}
          data={buildAnalysisData()}
        />
      )}

      {/* Branch B: 수동 4단계 */}
      {isManualStep && (
        <div className="min-h-screen bg-background flex items-center justify-center p-4">
          <div className="w-full max-w-[520px]">
            {/* 스텝 인디케이터 */}
            <div className="mb-8">
              <StepIndicator currentStep={getManualStep()} totalSteps={4} />
            </div>

            {phase === "step-category" && (
              <StepCategorySelect
                onNext={handleCategoryNext}
                initialData={manualInput.categories}
              />
            )}

            {phase === "step-audience" && (
              <StepTargetAudience
                onNext={handleAudienceNext}
                onPrev={handleAudiencePrev}
                initialData={{
                  gender: manualInput.gender,
                  ageGroup: manualInput.ageGroup,
                }}
              />
            )}

            {phase === "step-benchmark" && (
              <StepBenchmarkChannels
                onNext={handleBenchmarkNext}
                onSkip={handleBenchmarkSkip}
                onPrev={handleBenchmarkPrev}
                initialData={manualInput.benchmarkChannels}
              />
            )}

            {phase === "step-concept" && (
              <StepChannelConcept
                onNext={handleConceptNext}
                onPrev={handleConceptPrev}
                initialData={{
                  topicKeywords: manualInput.topicKeywords,
                  styleKeywords: manualInput.styleKeywords,
                }}
                selectedCategories={manualInput.categories}
              />
            )}
          </div>
        </div>
      )}

      {/* Branch B: 트렌드 추천 로딩 */}
      {phase === "loading-recommendation" && (
        <LoadingTrendRecommendation onComplete={handleLoadingComplete} apiStep={apiStep} />
      )}
    </div>
  )
}
