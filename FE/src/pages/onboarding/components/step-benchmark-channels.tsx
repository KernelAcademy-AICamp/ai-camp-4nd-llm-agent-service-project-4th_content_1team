"use client"

import { useState } from "react"
import { Button } from "../../../components/ui/button"
import { cn } from "../../../lib/utils"
import { ChannelSearch, type BenchmarkChannel } from "./channel-search"

export type { BenchmarkChannel }

export interface StepBenchmarkChannelsProps {
  onNext: (channels: BenchmarkChannel[]) => void
  onSkip: () => void
  onPrev: () => void
  initialData?: BenchmarkChannel[]
}

export function StepBenchmarkChannels({
  onNext,
  onSkip,
  onPrev,
  initialData = [],
}: StepBenchmarkChannelsProps) {
  const [channels, setChannels] = useState<BenchmarkChannel[]>(initialData)

  const handleAddChannel = (channel: BenchmarkChannel) => {
    if (channels.length >= 3) return
    if (channels.some((ch) => ch.channelId === channel.channelId)) return
    setChannels((prev) => [...prev, channel])
  }

  const handleRemoveChannel = (channelId: string) => {
    setChannels((prev) => prev.filter((ch) => ch.channelId !== channelId))
  }

  return (
    <div className="animate-fade-in-up">
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground mb-2 text-balance">
          지향하는 유튜버가 있나요?
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed">
          롤모델 유튜버를 검색해서 추가해주세요 (최대 3개, 선택사항)
        </p>
      </div>

      <div className="mb-10">
        <ChannelSearch
          selectedChannels={channels}
          onAddChannel={handleAddChannel}
          onRemoveChannel={handleRemoveChannel}
          maxChannels={3}
          searchLimit={10}
          placeholder="채널명 또는 @핸들로 검색"
          emptyTitle="아직 추가된 채널이 없어요"
          emptyDescription="채널명으로 검색해서 추가하거나, 건너뛸 수 있어요"
        />
      </div>

      <div className="flex justify-between">
        <Button
          variant="ghost"
          onClick={onPrev}
          className="text-muted-foreground hover:text-foreground px-6 py-5 rounded-xl"
        >
          이전
        </Button>
        <div className="flex gap-3">
          <Button
            variant="ghost"
            onClick={onSkip}
            className="text-muted-foreground hover:text-foreground px-6 py-5 rounded-xl"
          >
            건너뛰기
          </Button>
          <Button
            onClick={() => onNext(channels)}
            className={cn(
              "px-8 py-5 rounded-xl text-base font-semibold transition-all",
              channels.length > 0
                ? "bg-gradient-to-br from-[#2D2DFF] to-primary text-primary-foreground hover:shadow-[0_8px_32px_rgba(107,92,255,0.35)] hover:-translate-y-0.5"
                : "opacity-40"
            )}
          >
            다음
          </Button>
        </div>
      </div>
    </div>
  )
}
