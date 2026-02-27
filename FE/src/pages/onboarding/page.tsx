"use client"

import { useState, useCallback, useEffect } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { StepCategorySelect } from "@/pages/onboarding/components/step-category-select"
import { StepTargetAudience } from "@/pages/onboarding/components/step-target-audience"
import { StepBenchmarkChannels, type BenchmarkChannel } from "@/pages/onboarding/components/step-benchmark-channels"
import { StepChannelConcept } from "@/pages/onboarding/components/step-channel-concept"
import { LoadingChannelAnalysis } from "@/pages/onboarding/components/loading-channel-analysis"
import { ChannelAnalysisResult } from "@/pages/onboarding/components/channel-analysis-result"
import { StepIndicator } from "@/pages/onboarding/components/step-indicator"
import type { Gender } from "@/pages/onboarding/components/step-target-audience"

/* 플로우 단계 (스펙 순서) */
type FlowStep = "step1" | "step2" | "step3" | "step4" | "loading" | "result"

const FLOW_STEPS: FlowStep[] = ["step1", "step2", "step3", "step4"]
const STEP_NUMBER_MAP: Record<FlowStep, number> = {
  step1: 1,
  step2: 2,
  step3: 3,
  step4: 4,
  loading: 0,
  result: 0,
}

/* 페이지에서 수집하는 온보딩 데이터 */
interface OnboardingData {
  preferredCategories?: string[]
  targetGender?: Gender
  targetAgeGroup?: number
  benchmarkChannels?: BenchmarkChannel[]
  topicKeywords?: string[]
  styleKeywords?: string[]
}

const BRAND_NAME = "CreatorHub"

const FLOW_STEP_SEGMENTS: FlowStep[] = ["step1", "step2", "step3", "step4", "loading", "result"]

function getStepFromPath(pathname: string): FlowStep {
  const segment = pathname.replace(/^\/onboarding\/?/, "").toLowerCase() || "step1"
  return FLOW_STEP_SEGMENTS.includes(segment as FlowStep) ? (segment as FlowStep) : "step1"
}

export default function OnboardingPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [currentFlow, setCurrentFlow] = useState<FlowStep>(() => getStepFromPath(location.pathname))
  const [onboardingData, setOnboardingData] = useState<Partial<OnboardingData>>({})

  /* URL과 단계 동기화: 직접 주소 입력·뒤로가기 시 */
  useEffect(() => {
    const step = getStepFromPath(location.pathname)
    setCurrentFlow(step)
  }, [location.pathname])

  /* /onboarding 만 입력한 경우 step1으로 URL 통일 */
  useEffect(() => {
    if (location.pathname === "/onboarding" || location.pathname === "/onboarding/") {
      navigate("/onboarding/step1", { replace: true })
    }
  }, [location.pathname, navigate])

  const hasCompetitors = (onboardingData.benchmarkChannels ?? []).length > 0
  const currentStepNumber = STEP_NUMBER_MAP[currentFlow]
  const isStepView = FLOW_STEPS.includes(currentFlow)

  const handleStep1Complete = useCallback(
    (categories: string[]) => {
      setOnboardingData((prev) => ({ ...prev, preferredCategories: categories }))
      setCurrentFlow("step2")
      navigate("/onboarding/step2")
    },
    [navigate]
  )

  const handleStep2Complete = useCallback(
    (data: { gender: Gender; ageGroup: number }) => {
      setOnboardingData((prev) => ({
        ...prev,
        targetGender: data.gender,
        targetAgeGroup: data.ageGroup,
      }))
      setCurrentFlow("step3")
      navigate("/onboarding/step3")
    },
    [navigate]
  )

  const handleStep3Complete = useCallback(
    (channels: BenchmarkChannel[]) => {
      setOnboardingData((prev) => ({ ...prev, benchmarkChannels: channels }))
      setCurrentFlow("step4")
      navigate("/onboarding/step4")
    },
    [navigate]
  )

  const handleStep3Skip = useCallback(() => {
    setOnboardingData((prev) => ({ ...prev, benchmarkChannels: [] }))
    setCurrentFlow("step4")
    navigate("/onboarding/step4")
  }, [navigate])

  const handleStep4Complete = useCallback(
    (data: { topicKeywords: string[]; styleKeywords: string[] }) => {
      setOnboardingData((prev) => ({
        ...prev,
        topicKeywords: data.topicKeywords,
        styleKeywords: data.styleKeywords,
      }))
      setCurrentFlow("loading")
      navigate("/onboarding/loading")
    },
    [navigate]
  )

  const handleAnalysisComplete = useCallback(() => {
    setCurrentFlow("result")
    navigate("/onboarding/result")
  }, [navigate])

  const handleResultComplete = useCallback(() => {
    navigate("/explore")
  }, [navigate])

  const handlePrev = useCallback(
    (step: FlowStep) => {
      setCurrentFlow(step)
      navigate(`/onboarding/${step}`)
    },
    [navigate]
  )

  /* 로딩 화면 */
  if (currentFlow === "loading") {
    return (
      <LoadingChannelAnalysis
        onComplete={handleAnalysisComplete}
        hasCompetitors={hasCompetitors}
      />
    )
  }

  /* 결과 화면 */
  if (currentFlow === "result") {
    return (
      <div className="min-h-screen bg-background overflow-y-auto">
        <ChannelAnalysisResult
          onComplete={handleResultComplete}
          hasCompetitors={hasCompetitors}
        />
      </div>
    )
  }

  /* Step 1–4 공통 레이아웃 */
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="h-[66px] border-b border-[rgba(255,255,255,0.06)] flex items-center px-4 md:px-6 shrink-0 bg-[rgba(255,255,255,0.02)]">
        <div className="flex items-center justify-between w-full max-w-[800px] mx-auto">
          <span className="text-lg font-bold text-foreground tracking-tight">
            {BRAND_NAME}
          </span>
          {isStepView && (
            <StepIndicator currentStep={currentStepNumber} totalSteps={4} />
          )}
        </div>
      </header>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[800px] mx-auto px-4 py-8 md:px-6 md:py-12">
          {currentFlow === "step1" && (
            <StepCategorySelect
              onNext={handleStep1Complete}
              initialData={onboardingData.preferredCategories}
            />
          )}

          {currentFlow === "step2" && (
            <StepTargetAudience
              onNext={handleStep2Complete}
              onPrev={() => handlePrev("step1")}
              initialData={{
                gender: onboardingData.targetGender,
                ageGroup: onboardingData.targetAgeGroup,
              }}
            />
          )}

          {currentFlow === "step3" && (
            <StepBenchmarkChannels
              onNext={handleStep3Complete}
              onSkip={handleStep3Skip}
              onPrev={() => handlePrev("step2")}
              initialData={onboardingData.benchmarkChannels}
            />
          )}

          {currentFlow === "step4" && (
            <StepChannelConcept
              onNext={handleStep4Complete}
              onPrev={() => handlePrev("step3")}
              initialData={{
                topicKeywords: onboardingData.topicKeywords,
                styleKeywords: onboardingData.styleKeywords,
              }}
              selectedCategories={onboardingData.preferredCategories ?? []}
            />
          )}
        </div>
      </main>
    </div>
  )
}
