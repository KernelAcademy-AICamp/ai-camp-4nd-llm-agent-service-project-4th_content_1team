"use client"

import { useNavigate } from "react-router-dom"
import { ChannelAnalysisResult } from "@/pages/onboarding/components/channel-analysis-result"

/**
 * 로그인 후 페르소나가 있을 때 보여주는 채널 분석 결과 전용 화면.
 * CTA 클릭 시 /explore 로 이동.
 */
export default function ChannelResultPage() {
  const navigate = useNavigate()

  const handleComplete = () => {
    navigate("/explore")
  }

  return (
    <div className="min-h-screen bg-background overflow-y-auto">
      <ChannelAnalysisResult onComplete={handleComplete} hasCompetitors={false} />
    </div>
  )
}
