"use client"

import React, { useState } from "react"
import { Button } from "../../../components/ui/button"
import {
  Gamepad2,
  GraduationCap,
  UtensilsCrossed,
  Dumbbell,
  Palette,
  Music,
  Camera,
  Briefcase,
  Clapperboard,
} from "lucide-react"
import { cn } from "../../../lib/utils"

/* 스펙 § Step 1: 9개 카테고리, 최소 1개·최대 2개 선택 */
const CATEGORIES: { id: string; label: string; icon: React.ElementType }[] = [
  { id: "gaming", label: "게임", icon: Gamepad2 },
  { id: "education", label: "교육/정보", icon: GraduationCap },
  { id: "food", label: "먹방/요리", icon: UtensilsCrossed },
  { id: "fitness", label: "운동/건강", icon: Dumbbell },
  { id: "art", label: "예술/창작", icon: Palette },
  { id: "music", label: "음악", icon: Music },
  { id: "vlog", label: "브이로그", icon: Camera },
  { id: "business", label: "비즈니스", icon: Briefcase },
  { id: "entertainment", label: "엔터테인먼트", icon: Clapperboard },
]

export interface StepCategorySelectProps {
  onNext: (categories: string[]) => void
  initialData?: string[]
}

export function StepCategorySelect({
  onNext,
  initialData = [],
}: StepCategorySelectProps) {
  const [selected, setSelected] = useState<string[]>(initialData)
  const [warning, setWarning] = useState<string | null>(null)

  const handleToggle = (id: string) => {
    setWarning(null)

    if (selected.includes(id)) {
      setSelected((prev) => prev.filter((item) => item !== id))
      return
    }

    if (selected.length >= 2) {
      setWarning("카테고리는 최대 2개까지 선택할 수 있습니다.")
      return
    }

    setSelected((prev) => [...prev, id])
  }

  const handleNextClick = () => {
    if (selected.length >= 1) {
      onNext(selected)
    }
  }

  const isValid = selected.length >= 1

  return (
    <div className="animate-fade-in-up">
      {/* 헤딩 */}
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground mb-2 text-balance">
          어떤 콘텐츠를 만들고 싶으세요?
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed">
          관심 있는 카테고리를 선택해주세요 (최대 2개)
        </p>
      </div>

      {/* 2개 초과 선택 시 안내 */}
      {warning && (
        <p className="mb-4 text-sm text-amber-500" role="alert">
          {warning}
        </p>
      )}

      {/* 카테고리 그리드: 3x3 (mobile 2x3) */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 mb-10">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon
          const isSelected = selected.includes(cat.id)

          return (
            <button
              key={cat.id}
              type="button"
              onClick={() => handleToggle(cat.id)}
              className={cn(
                "flex flex-col items-center gap-3 rounded-xl border p-5 transition-all",
                "hover:border-primary/30 hover:bg-primary/5",
                isSelected
                  ? "border-primary bg-primary/10 shadow-[0_0_20px_rgba(107,92,255,0.15)]"
                  : "border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)]"
              )}
            >
              <div
                className={cn(
                  "flex h-12 w-12 items-center justify-center rounded-lg transition-colors",
                  isSelected
                    ? "bg-primary/20 text-primary"
                    : "bg-[rgba(255,255,255,0.04)] text-muted-foreground"
                )}
              >
                <Icon className="h-6 w-6" />
              </div>
              <span
                className={cn(
                  "text-sm font-medium transition-colors",
                  isSelected ? "text-primary" : "text-muted-foreground"
                )}
              >
                {cat.label}
              </span>
            </button>
          )
        })}
      </div>

      {/* 다음 버튼 */}
      <div className="flex justify-end">
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
