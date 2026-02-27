"use client"

import { useState, useMemo, useEffect } from "react"
import { Button } from "../../../components/ui/button"
import { Input } from "../../../components/ui/input"
import { X, Search, Loader2 } from "lucide-react"
import { cn } from "../../../lib/utils"
import { searchChannels } from "../../../lib/api/services/channel.service"
import type { ChannelSearchResult } from "../../../lib/api/types/channel.types"

export interface BenchmarkChannel {
  channelId: string
  title: string
  customUrl?: string
  subscriberCount: number
  thumbnailUrl?: string
}

function toBenchmarkChannel(ch: ChannelSearchResult): BenchmarkChannel {
  return {
    channelId: ch.channel_id,
    title: ch.title,
    customUrl: ch.custom_url,
    subscriberCount: ch.subscriber_count,
    thumbnailUrl: ch.thumbnail_url,
  }
}

function formatSubscribers(count: number): string {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}만`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}천`
  return `${count}`
}

function getInitial(name: string): string {
  const firstChar = name.charAt(0)
  if (/[가-힣]/.test(firstChar)) return firstChar
  return firstChar.toUpperCase()
}

export interface ChannelSearchProps {
  selectedChannels: BenchmarkChannel[]
  onAddChannel: (channel: BenchmarkChannel) => void
  onRemoveChannel: (channelId: string) => void
  maxChannels?: number
  searchLimit?: number
  placeholder?: string
  emptyTitle?: string
  emptyDescription?: string
}

export function ChannelSearch({
  selectedChannels,
  onAddChannel,
  onRemoveChannel,
  maxChannels = 3,
  searchLimit = 10,
  placeholder = "채널명 또는 @핸들로 검색",
  emptyTitle = "아직 추가된 채널이 없어요",
  emptyDescription = "채널명으로 검색해서 추가하거나, 건너뛸 수 있어요",
}: ChannelSearchProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [isSearching, setIsSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<BenchmarkChannel[]>([])
  const [hasSearched, setHasSearched] = useState(false)
  const [searchCount, setSearchCount] = useState(0)
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!toastMessage) return
    const t = setTimeout(() => setToastMessage(null), 3000)
    return () => clearTimeout(t)
  }, [toastMessage])

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    if (searchCount >= searchLimit) {
      setToastMessage(`검색 횟수 제한(${searchLimit}회)을 초과했습니다.`)
      return
    }

    setIsSearching(true)
    setHasSearched(true)
    setSearchCount((c) => c + 1)

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

  const handleAdd = (channel: BenchmarkChannel) => {
    if (selectedChannels.length >= maxChannels) return
    if (selectedChannels.some((ch) => ch.channelId === channel.channelId)) return
    onAddChannel(channel)
    setSearchResults([])
    setSearchQuery("")
    setHasSearched(false)
  }

  const addedIds = useMemo(
    () => new Set(selectedChannels.map((ch) => ch.channelId)),
    [selectedChannels]
  )

  const isSearchDisabled =
    isSearching || selectedChannels.length >= maxChannels || searchCount >= searchLimit

  return (
    <div className="space-y-6">
      {/* 검색 입력 */}
      <div className="flex gap-2">
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="flex-1 h-11 rounded-lg border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] text-foreground placeholder:text-muted-foreground/60"
          disabled={isSearchDisabled}
        />
        <Button
          onClick={handleSearch}
          disabled={
            isSearching ||
            selectedChannels.length >= maxChannels ||
            !searchQuery.trim() ||
            searchCount >= searchLimit
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

      {/* 검색 결과 */}
      {searchResults.length > 0 && (
        <div className="rounded-xl border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)] overflow-hidden">
          <p className="text-xs text-muted-foreground px-4 py-2.5 border-b border-[rgba(255,255,255,0.06)]">
            검색 결과
          </p>
          {searchResults.map((result) => {
            const isAdded = addedIds.has(result.channelId)
            return (
              <button
                key={result.channelId}
                type="button"
                onClick={() => !isAdded && handleAdd(result)}
                disabled={isAdded}
                className={cn(
                  "flex items-center gap-3 w-full px-4 py-3 text-left transition-colors border-b border-[rgba(255,255,255,0.04)] last:border-b-0",
                  isAdded
                    ? "opacity-40 cursor-not-allowed"
                    : "hover:bg-[rgba(255,255,255,0.04)] cursor-pointer"
                )}
              >
                {result.thumbnailUrl ? (
                  <img
                    src={result.thumbnailUrl}
                    alt=""
                    className="h-8 w-8 shrink-0 rounded-full object-cover bg-muted"
                  />
                ) : (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">
                    {getInitial(result.title)}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{result.title}</p>
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
        <div className="text-center py-6 rounded-xl border border-dashed border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.01)]">
          <p className="text-sm text-muted-foreground">검색 결과가 없습니다</p>
          <p className="text-xs text-muted-foreground/60 mt-1">다른 키워드로 검색해보세요</p>
        </div>
      )}

      {/* 추가된 채널 리스트 */}
      {selectedChannels.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            추가된 채널 ({selectedChannels.length}/{maxChannels})
          </p>
          <div className="space-y-2">
            {selectedChannels.map((channel) => (
              <div
                key={channel.channelId}
                className="flex items-center gap-3 px-4 py-3 rounded-xl border border-primary/20 bg-primary/5 transition-all"
              >
                {channel.thumbnailUrl ? (
                  <img
                    src={channel.thumbnailUrl}
                    alt=""
                    className="h-9 w-9 shrink-0 rounded-full object-cover bg-muted"
                  />
                ) : (
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/20 text-primary text-sm font-bold">
                    {getInitial(channel.title)}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{channel.title}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {channel.customUrl && `${channel.customUrl} · `}
                    구독자 {formatSubscribers(channel.subscriberCount)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onRemoveChannel(channel.channelId)}
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
      {selectedChannels.length === 0 && !hasSearched && (
        <div className="flex flex-col items-center justify-center py-12 rounded-xl border border-dashed border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.01)]">
          <p className="text-sm text-muted-foreground mb-1">{emptyTitle}</p>
          <p className="text-xs text-muted-foreground/60">{emptyDescription}</p>
        </div>
      )}

      {/* 토스트 */}
      {toastMessage && (
        <div
          role="alert"
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-3 rounded-lg bg-amber-500/90 text-amber-950 text-sm font-medium shadow-lg animate-in fade-in slide-in-from-bottom-2 duration-200"
        >
          {toastMessage}
        </div>
      )}
    </div>
  )
}
