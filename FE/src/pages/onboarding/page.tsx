"use client"

import { useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
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

export default function OnboardingPage() {
  const navigate = useNavigate()
  const [currentFlow, setCurrentFlow] = useState<FlowStep>("step1")
  const [onboardingData, setOnboardingData] = useState<Partial<OnboardingData>>({})

  const hasCompetitors = (onboardingData.benchmarkChannels ?? []).length > 0
  const currentStepNumber = STEP_NUMBER_MAP[currentFlow]
  const isStepView = FLOW_STEPS.includes(currentFlow)

  const handleStep1Complete = useCallback((categories: string[]) => {
    setOnboardingData((prev) => ({ ...prev, preferredCategories: categories }))
    setCurrentFlow("step2")
  }, [])

  const handleStep2Complete = useCallback((data: { gender: Gender; ageGroup: number }) => {
    setOnboardingData((prev) => ({
      ...prev,
      targetGender: data.gender,
      targetAgeGroup: data.ageGroup,
    }))
    setCurrentFlow("step3")
  }, [])

  const handleStep3Complete = useCallback((channels: BenchmarkChannel[]) => {
    setOnboardingData((prev) => ({ ...prev, benchmarkChannels: channels }))
    setCurrentFlow("step4")
  }, [])

  const handleStep3Skip = useCallback(() => {
    setOnboardingData((prev) => ({ ...prev, benchmarkChannels: [] }))
    setCurrentFlow("step4")
  }, [])

  const handleStep4Complete = useCallback(
    (data: { topicKeywords: string[]; styleKeywords: string[] }) => {
      setOnboardingData((prev) => ({
        ...prev,
        topicKeywords: data.topicKeywords,
        styleKeywords: data.styleKeywords,
      }))
      setCurrentFlow("loading")
    },
    []
  )

  const handleAnalysisComplete = useCallback(() => {
    setCurrentFlow("result")
  }, [])

  const handleResultComplete = useCallback(() => {
    navigate("/explore")
  }, [navigate])

  const handlePrev = useCallback((step: FlowStep) => {
    setCurrentFlow(step)
  }, [])

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
