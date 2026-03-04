"use client"

import { cn } from "../../../lib/utils"

export interface StepIndicatorProps {
  currentStep: number
  totalSteps: number
}

export function StepIndicator({ currentStep, totalSteps }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-1.5" aria-label={`단계 ${currentStep} / ${totalSteps}`}>
      {Array.from({ length: totalSteps }, (_, i) => (
        <span
          key={i}
          className={cn(
            "h-1.5 rounded-full transition-all duration-200",
            i + 1 <= currentStep ? "w-5 bg-primary" : "w-1.5 bg-muted"
          )}
          aria-hidden
        />
      ))}
      <span className="ml-2 text-xs text-muted-foreground tabular-nums">
        {currentStep}/{totalSteps}
      </span>
    </div>
  )
}
