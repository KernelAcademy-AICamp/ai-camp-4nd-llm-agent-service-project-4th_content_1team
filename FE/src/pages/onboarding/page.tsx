"use client"

import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "../../components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card"
import { Play, Check, Loader2 } from "lucide-react"
import { generatePersona } from "../../lib/api"
import { generateTrendTopics } from "../../lib/api/services"
import type { PersonaResponse } from "../../lib/api/types"

export default function OnboardingPage() {
  const navigate = useNavigate()

  // 상태
  const [isAnalyzing, setIsAnalyzing] = useState(true)
  const [isGeneratingTopics, setIsGeneratingTopics] = useState(false)
  const [persona, setPersona] = useState<PersonaResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // StrictMode 중복 호출 방지
  const hasCalledRef = useRef(false)

  // 페이지 진입 시 페르소나 생성 → 트렌드 추천 생성
  useEffect(() => {
    if (hasCalledRef.current) return
    hasCalledRef.current = true

    const initializeChannel = async () => {
      try {
        // 1단계: 페르소나 생성
        setIsAnalyzing(true)
        setError(null)

        const personaResponse = await generatePersona()

        if (!personaResponse.success || !personaResponse.persona) {
          setError(personaResponse.message || "채널 분석에 실패했습니다.")
          setIsAnalyzing(false)
          return
        }

        setPersona(personaResponse.persona)
        setIsAnalyzing(false)

        // 2단계: 트렌드 추천 생성
        setIsGeneratingTopics(true)

        const topicsResponse = await generateTrendTopics()

        if (!topicsResponse.success) {
          console.error("트렌드 추천 생성 실패:", topicsResponse.message)
          // 추천 실패해도 진행 가능 (explore에서 빈 상태 표시)
        }

        setIsGeneratingTopics(false)
      } catch (err: any) {
        console.error("초기화 실패:", err)
        setError(err.response?.data?.detail || "채널 분석 중 오류가 발생했습니다.")
        setIsAnalyzing(false)
        setIsGeneratingTopics(false)
      }
    }

    initializeChannel()
  }, [])

  // 분석된 카테고리 텍스트
  const getAnalyzedCategoryText = () => {
    if (!persona?.analyzed_categories || persona.analyzed_categories.length === 0) {
      return "분석된 카테고리 없음"
    }
    return persona.analyzed_categories.join(", ")
  }

  // 시작하기 클릭
  const handleStart = () => {
    navigate('/explore')
  }

  const isLoading = isAnalyzing || isGeneratingTopics

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
            <Play className="w-5 h-5 text-primary-foreground fill-current" />
          </div>
          <span className="text-xl font-bold text-foreground">CreatorHub</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-6">
        <Card className="w-full max-w-2xl border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">
              {isAnalyzing
                ? "채널을 분석하고 있어요"
                : isGeneratingTopics
                ? "맞춤 주제를 찾고 있어요"
                : error
                ? "분석 중 문제가 발생했어요"
                : "준비가 완료되었어요!"}
            </CardTitle>
            <CardDescription>
              {isAnalyzing
                ? "잠시만 기다려 주세요..."
                : isGeneratingTopics
                ? "트렌드를 분석하여 최적의 주제를 추천해 드릴게요"
                : error
                ? error
                : "채널 분석과 주제 추천이 완료되었습니다"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* 로딩 상태 */}
            {isLoading && (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="w-16 h-16 text-primary animate-spin mb-6" />
                <p className="text-muted-foreground text-center">
                  {isAnalyzing
                    ? <>채널의 영상 데이터를 분석하여<br />맞춤형 콘텐츠를 추천해 드릴게요</>
                    : <>트렌드 데이터를 수집하고<br />최적의 주제를 찾고 있어요</>
                  }
                </p>
              </div>
            )}

            {/* 에러 상태 */}
            {!isLoading && error && (
              <div className="flex flex-col items-center justify-center py-8">
                <Button
                  onClick={() => window.location.reload()}
                  className="bg-primary hover:bg-primary/90"
                >
                  다시 시도하기
                </Button>
              </div>
            )}

            {/* 완료 상태 */}
            {!isLoading && !error && (
              <div className="p-4 rounded-xl bg-primary/10 border border-primary/20">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                    <Check className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">분석 완료</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      채널 카테고리: <span className="text-primary font-medium">{getAnalyzedCategoryText()}</span>
                    </p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>

          {/* 하단 버튼 - 모든 처리 완료 후에만 표시 */}
          {!isLoading && !error && (
            <div className="p-6 pt-0 flex justify-end">
              <Button
                onClick={handleStart}
                className="gap-2 bg-primary hover:bg-primary/90"
              >
                시작하기
                <Check className="w-4 h-4" />
              </Button>
            </div>
          )}
        </Card>
      </main>
    </div>
  )
}
