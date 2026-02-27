"use client"

import React, { useState, useEffect } from "react"
import { Check, Loader2, User, Palette, Sparkles, Database } from "lucide-react"
import { cn } from "@/lib/utils"

export interface LoadingPersonaCreationProps {
  onComplete: () => void
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

/** 분기 2: step-channel-concept 직후 → 페르소나 생성 로딩 → 완료 시 onComplete(explore 이동) */
export function LoadingPersonaCreation({ onComplete }: LoadingPersonaCreationProps) {
  const [progress, setProgress] = useState(0)
  const [step, setStep] = useState(0)

  const steps: { label: string; detail?: string; icon: React.ElementType }[] = [
    { label: "선택 정보 정리", icon: Palette },
    { label: "페르소나 프로필 생성", detail: "채널 성향 분석 중...", icon: User },
    { label: "콘텐츠 방향 설정", icon: Sparkles },
    { label: "저장 완료", icon: Database },
  ]

  useEffect(() => {
    let completed = false
    const progressInterval = setInterval(() => {
      setProgress((p) => (p >= 100 ? 100 : p + 5))
    }, 350)

    const stepInterval = setInterval(() => {
      setStep((s) => (s >= steps.length - 1 ? steps.length - 1 : s + 1))
    }, 900)

    const finishTimeout = setTimeout(() => {
      if (!completed) {
        completed = true
        onComplete()
      }
    }, 3600)

    return () => {
      clearInterval(progressInterval)
      clearInterval(stepInterval)
      clearTimeout(finishTimeout)
    }
  }, [onComplete])

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="rounded-xl border border-border bg-card p-5 shadow-lg w-full max-w-[320px]">
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1.5">
            <span className="text-muted-foreground">진행률</span>
            <span className="font-medium text-foreground">{Math.min(progress, 100)}%</span>
          </div>
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(progress, 100)}%` }}
            />
          </div>
        </div>

        <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide mb-2">
          페르소나 생성
        </p>
        <div className="space-y-0.5">
          {steps.map((s, i) => (
            <StepItem
              key={i}
              status={i < step ? "completed" : i === step ? "processing" : "pending"}
              icon={s.icon}
              label={s.label}
              detail={i === step ? s.detail : undefined}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
