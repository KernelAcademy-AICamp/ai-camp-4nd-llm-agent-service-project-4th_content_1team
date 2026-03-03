"use client"

import React, { useState, useEffect, useRef } from "react"
import { Check, FileText, Loader2, BarChart3, MessageSquare, Brain, TrendingUp } from "lucide-react"
import { cn } from "../../../lib/utils"

export interface LoadingChannelAnalysisProps {
  onComplete: () => void
  hasCompetitors: boolean
  apiStep: number // 0=시작전, 1=페르소나중, 2=페르소나완료+트렌드중, 3=전부완료
}

type StepStatus = "completed" | "processing" | "pending"

interface StepItemProps {
  status: StepStatus
  icon: React.ElementType
  label: string
  detail?: string
}

function StepItem({ status, icon: Icon, label, detail }: StepItemProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs",
        status === "completed" && "text-green-600 dark:text-green-400",
        status === "processing" && "text-primary",
        status === "pending" && "text-muted-foreground"
      )}
    >
      {status === "completed" && <Check className="h-3.5 w-3.5 shrink-0" />}
      {status === "processing" && <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />}
      {status === "pending" && <Icon className="h-3.5 w-3.5 shrink-0 opacity-60" />}
      <div className="min-w-0">
        <span>{label}</span>
        {detail && <span className="ml-1 text-muted-foreground">{detail}</span>}
      </div>
    </div>
  )
}

// 스텝 정의
// apiStep=1 구간 (generatePersona): 스텝 0~4
// apiStep=2 구간 (generateTrendTopics): 스텝 5
const STEPS = [
  { label: "채널 정보 수집", icon: FileText, phase: 1, timerDelay: 2000 },
  { label: "영상 데이터 수집", icon: FileText, phase: 1, timerDelay: 5000 },
  { label: "영상 패턴 분석", icon: BarChart3, phase: 1, timerDelay: 8000 },
  { label: "시청자 반응 분석", icon: MessageSquare, phase: 1, timerDelay: 8000 },
  { label: "페르소나 생성", icon: Brain, phase: 1, timerDelay: null }, // API 완료 대기
  { label: "트렌드 추천 생성", icon: TrendingUp, phase: 2, timerDelay: null }, // API 완료 대기
]

export function LoadingChannelAnalysis({ onComplete, apiStep }: LoadingChannelAnalysisProps) {
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set())
  const [currentStep, setCurrentStep] = useState(0)
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])
  const onCompleteCalledRef = useRef(false)

  // apiStep=1 진입 시: 타이머 스텝들 시작
  useEffect(() => {
    if (apiStep < 1) return

    // phase 1의 타이머 스텝들 (0~3) 순차 실행
    let accumulated = 0
    const phase1TimerSteps = STEPS
      .map((s, i) => ({ ...s, index: i }))
      .filter((s) => s.phase === 1 && s.timerDelay !== null)

    phase1TimerSteps.forEach((step) => {
      accumulated += step.timerDelay!
      const timer = setTimeout(() => {
        setCompletedSteps((prev) => new Set([...prev, step.index]))
        setCurrentStep(step.index + 1)
      }, accumulated)
      timersRef.current.push(timer)
    })

    return () => {
      timersRef.current.forEach(clearTimeout)
      timersRef.current = []
    }
  }, [apiStep >= 1]) // eslint-disable-line react-hooks/exhaustive-deps

  // apiStep=2: 페르소나 완료 → 스텝 4 체크, 스텝 5 스피너
  useEffect(() => {
    if (apiStep < 2) return
    setCompletedSteps((prev) => {
      const next = new Set(prev)
      for (let i = 0; i <= 4; i++) next.add(i)
      return next
    })
    setCurrentStep(5)
  }, [apiStep])

  // apiStep=3: 전부 완료 → 스텝 5 체크, onComplete 호출
  useEffect(() => {
    if (apiStep < 3) return
    setCompletedSteps((prev) => {
      const next = new Set(prev)
      for (let i = 0; i <= 5; i++) next.add(i)
      return next
    })
    // 체크 애니메이션 보여준 후 완료
    const timer = setTimeout(() => {
      if (!onCompleteCalledRef.current) {
        onCompleteCalledRef.current = true
        onComplete()
      }
    }, 800)
    return () => clearTimeout(timer)
  }, [apiStep, onComplete])

  // 스텝 상태 결정
  const getStepStatus = (index: number): StepStatus => {
    if (completedSteps.has(index)) return "completed"
    if (index === currentStep) return "processing"
    return "pending"
  }

  // 프로그레스 바 계산
  const progress = Math.round((completedSteps.size / STEPS.length) * 100)

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="rounded-xl border border-border bg-card p-5 shadow-lg w-full max-w-[320px]">
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1.5">
            <span className="text-muted-foreground">분석 진행률</span>
            <span className="font-medium text-foreground">{progress}%</span>
          </div>
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide mb-2">
          내 채널 분석
        </p>
        <div className="space-y-0.5">
          {STEPS.map((s, i) => (
            <StepItem
              key={i}
              status={getStepStatus(i)}
              icon={s.icon}
              label={s.label}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
