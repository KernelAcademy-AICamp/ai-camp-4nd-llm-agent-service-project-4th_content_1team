"use client"

import { useState } from "react"
import { Button } from "../../../components/ui/button"
import { cn } from "../../../lib/utils"

/* 스펙 § Step 2: 성별(male/female/any), 연령대 버튼 10~50대+ */
export type Gender = "male" | "female" | "any"

const GENDER_OPTIONS: { value: Gender; label: string }[] = [
  { value: "male", label: "남성" },
  { value: "female", label: "여성" },
  { value: "any", label: "무관" },
]

const AGE_OPTIONS: { value: number; label: string }[] = [
  { value: 10, label: "10대" },
  { value: 20, label: "20대" },
  { value: 30, label: "30대" },
  { value: 40, label: "40대" },
  { value: 50, label: "50대+" },
]

export interface StepTargetAudienceProps {
  onNext: (data: { gender: Gender; ageGroup: number }) => void
  onPrev: () => void
  initialData?: { gender?: Gender; ageGroup?: number }
}

export function StepTargetAudience({
  onNext,
  onPrev,
  initialData,
}: StepTargetAudienceProps) {
  const [gender, setGender] = useState<Gender | null>(initialData?.gender ?? null)
  const [ageGroup, setAgeGroup] = useState<number | null>(
    initialData?.ageGroup ?? null
  )

  const handleNextClick = () => {
    if (gender !== null && ageGroup !== null) {
      onNext({ gender, ageGroup })
    }
  }

  const isValid = gender !== null && ageGroup !== null

  return (
    <div className="animate-fade-in-up">
      {/* 헤딩 */}
      <div className="mb-10">
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground mb-2 text-balance">
          타겟 시청자를 알려주세요
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed">
          주요 시청자의 성별과 연령대를 선택해주세요
        </p>
      </div>

      {/* 성별 선택 */}
      <div className="mb-10">
        <label className="text-sm font-semibold text-foreground mb-4 block">
          성별
        </label>
        <div className="flex gap-3">
          {GENDER_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setGender(option.value)}
              className={cn(
                "flex-1 py-4 rounded-xl border text-sm font-medium transition-all",
                gender === option.value
                  ? "border-primary bg-primary/10 text-primary shadow-[0_0_16px_rgba(107,92,255,0.12)]"
                  : "border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)] text-muted-foreground hover:border-primary/20 hover:bg-primary/5"
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* 연령대 버튼 (스펙: Slider → Button Group) */}
      <div className="mb-12">
        <label className="text-sm font-semibold text-foreground mb-2 block">
          주 타겟 연령대
        </label>
        <p className="text-xs text-muted-foreground mb-5">
          콘텐츠의 주요 대상 연령대를 선택하세요
        </p>

        <div className="grid grid-cols-3 gap-3 md:grid-cols-5">
          {AGE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setAgeGroup(option.value)}
              className={cn(
                "py-4 rounded-xl border text-sm font-medium transition-all",
                ageGroup === option.value
                  ? "border-primary bg-primary/10 text-primary shadow-[0_0_16px_rgba(107,92,255,0.12)]"
                  : "border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)] text-muted-foreground hover:border-primary/20 hover:bg-primary/5"
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* 네비게이션 버튼 */}
      <div className="flex justify-between">
        <Button
          variant="ghost"
          onClick={onPrev}
          className="text-muted-foreground hover:text-foreground px-6 py-5 rounded-xl"
        >
          이전
        </Button>
        <Button
          onClick={handleNextClick}
          disabled={!isValid}
          className={cn(
            "px-8 py-5 rounded-xl text-base font-semibold transition-all",
            isValid
              ? "bg-gradient-to-br from-[#2D2DFF] to-primary text-primary-foreground hover:shadow-[0_8px_32px_rgba(107,92,255,0.35)] hover:-translate-y-0.5"
              : "opacity-40"
          )}
        >
          다음
        </Button>
      </div>
    </div>
  )
}
