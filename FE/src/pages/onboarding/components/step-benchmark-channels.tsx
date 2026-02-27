"use client"

import { useState, useMemo } from "react"
import { Button } from "../../../components/ui/button"
import { Input } from "../../../components/ui/input"
import { X, Search, Loader2, AlertTriangle } from "lucide-react"
import { cn } from "../../../lib/utils"
import { searchChannels } from "../../../lib/api/services/channel.service"
import type { ChannelSearchResult } from "../../../lib/api/types/channel.types"

export interface BenchmarkChannel {
  channelId: string
  title: string
  customUrl?: string
  subscriberCount: number
}

/* 채널 분석 메뉴와 동일: API 응답 → UI 타입 변환 */
function toBenchmarkChannel(ch: ChannelSearchResult): BenchmarkChannel {
  return {
    channelId: ch.channel_id,
    title: ch.title,
    customUrl: ch.custom_url,
    subscriberCount: ch.subscriber_count,
  }
}

export interface StepBenchmarkChannelsProps {
  onNext: (channels: BenchmarkChannel[]) => void
  onSkip: () => void
  onPrev: () => void
  initialData?: BenchmarkChannel[]
}

/* 구독자 수 포맷 */
function formatSubscribers(count: number): string {
  if (count >= 10000) {
    return `${(count / 10000).toFixed(1)}만`
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}천`
  }
  return `${count}`
}

/* 채널명 첫 글자 추출 */
function getInitial(name: string): string {
  const firstChar = name.charAt(0)
  if (/[가-힣]/.test(firstChar)) return firstChar
  return firstChar.toUpperCase()
}

export function StepBenchmarkChannels({
  onNext,
  onSkip,
  onPrev,
  initialData = [],
}: StepBenchmarkChannelsProps) {
  const [channels, setChannels] = useState<BenchmarkChannel[]>(initialData)
  const [searchQuery, setSearchQuery] = useState("")
  const [isSearching, setIsSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<BenchmarkChannel[]>([])
  const [hasSearched, setHasSearched] = useState(false)

  /* 채널 검색 — 채널 분석 메뉴와 동일한 searchChannels API 사용 */
  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    setIsSearching(true)
    setHasSearched(true)

    try {
      const response = await searchChannels(searchQuery.trim())
      const list = (response.channels ?? []).map(toBenchmarkChannel)
      setSearchResults(list)
    } catch (err) {
      console.error("채널 검색 실패:", err)
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleSearch()
    }
  }

  const handleAddChannel = (channel: BenchmarkChannel) => {
    if (channels.length >= 3) return
    if (channels.some((ch) => ch.channelId === channel.channelId)) return
    setChannels((prev) => [...prev, channel])
    setSearchResults([])
    setSearchQuery("")
    setHasSearched(false)
  }

  const handleRemoveChannel = (channelId: string) => {
    setChannels((prev) => prev.filter((ch) => ch.channelId !== channelId))
  }

  const handleNextClick = () => {
    onNext(channels)
  }

  /* 이미 추가된 채널 ID 목록 */
  const addedIds = useMemo(
    () => new Set(channels.map((ch) => ch.channelId)),
    [channels]
  )

  return (
    <div className="animate-fade-in-up">
      {/* 헤딩 */}
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground mb-2 text-balance">
          지향하는 유튜버가 있나요?
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed">
          롤모델 유튜버를 검색해서 추가해주세요 (최대 3개, 선택사항)
        </p>
      </div>

      {/* Quota 경고 안내 */}
      <div className="flex items-start gap-2.5 mb-6 px-3.5 py-3 rounded-lg bg-amber-500/5 border border-amber-500/15">
        <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-muted-foreground leading-relaxed">
          채널 분석은 API 할당량을 사용합니다. 정확한 채널명으로 검색해주세요.
        </p>
      </div>

      {/* 채널 검색 */}
      <div className="mb-6">
        <div className="flex gap-2">
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="채널명 또는 @핸들로 검색"
            className="flex-1 h-11 rounded-lg border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] text-foreground placeholder:text-muted-foreground/60"
            disabled={isSearching || channels.length >= 3}
          />
          <Button
            onClick={handleSearch}
            disabled={
              isSearching || channels.length >= 3 || !searchQuery.trim()
            }
            className="h-11 px-4 rounded-lg bg-primary/20 text-primary hover:bg-primary/30 border border-primary/20"
            variant="ghost"
          >
            {isSearching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* 검색 결과 리스트 */}
      {searchResults.length > 0 && (
        <div className="mb-6 rounded-xl border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)] overflow-hidden">
          <p className="text-xs text-muted-foreground px-4 py-2.5 border-b border-[rgba(255,255,255,0.06)]">
            검색 결과
          </p>
          {searchResults.map((result) => {
            const isAdded = addedIds.has(result.channelId)
            return (
              <button
                key={result.channelId}
                type="button"
                onClick={() => !isAdded && handleAddChannel(result)}
                disabled={isAdded}
                className={cn(
                  "flex items-center gap-3 w-full px-4 py-3 text-left transition-colors border-b border-[rgba(255,255,255,0.04)] last:border-b-0",
                  isAdded
                    ? "opacity-40 cursor-not-allowed"
                    : "hover:bg-[rgba(255,255,255,0.04)] cursor-pointer"
                )}
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary text-xs font-bold">
                  {getInitial(result.title)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {result.title}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {result.customUrl && `${result.customUrl} · `}
                    구독자 {formatSubscribers(result.subscriberCount)}
                  </p>
                </div>
                <span className="text-xs text-primary font-medium shrink-0">
                  {isAdded ? "추가됨" : "추가"}
                </span>
              </button>
            )
          })}
        </div>
      )}

      {/* 검색 결과 없음 */}
      {hasSearched && !isSearching && searchResults.length === 0 && (
        <div className="mb-6 text-center py-6 rounded-xl border border-dashed border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.01)]">
          <p className="text-sm text-muted-foreground">검색 결과가 없습니다</p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            다른 키워드로 검색해보세요
          </p>
        </div>
      )}

      {/* 추가된 채널 리스트 */}
      {channels.length > 0 && (
        <div className="mb-10">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            추가된 채널 ({channels.length}/3)
          </p>
          <div className="space-y-2">
            {channels.map((channel) => (
              <div
                key={channel.channelId}
                className="flex items-center gap-3 px-4 py-3 rounded-xl border border-primary/20 bg-primary/5 transition-all"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/20 text-primary text-sm font-bold">
                  {getInitial(channel.title)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {channel.title}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {channel.customUrl && `${channel.customUrl} · `}
                    구독자 {formatSubscribers(channel.subscriberCount)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveChannel(channel.channelId)}
                  className="p-1.5 rounded-md hover:bg-[rgba(255,255,255,0.08)] transition-colors text-muted-foreground hover:text-foreground"
                  aria-label={`${channel.title} 삭제`}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 빈 상태 */}
      {channels.length === 0 && !hasSearched && (
        <div className="flex flex-col items-center justify-center py-12 rounded-xl border border-dashed border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.01)] mb-10">
          <p className="text-sm text-muted-foreground mb-1">
            아직 추가된 채널이 없어요
          </p>
          <p className="text-xs text-muted-foreground/60">
            채널명으로 검색해서 추가하거나, 건너뛸 수 있어요
          </p>
        </div>
      )}

      {/* 네비게이션 버튼 */}
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
            onClick={handleNextClick}
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
