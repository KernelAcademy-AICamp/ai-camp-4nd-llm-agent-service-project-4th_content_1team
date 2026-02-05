"use client"

import { useEffect, useState, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Badge } from "../../../components/ui/badge"
import { Button } from "../../../components/ui/button"
import { ScrollArea, ScrollBar } from "../../../components/ui/scroll-area"
import {
  Sparkles,
  Loader2,
  RefreshCw,
  Plus,
  Flame,
  Clock,
  TrendingUp,
  User,
  Zap,
  Calendar,
} from "lucide-react"
import {
  getTopics,
  getTopicsStatus,
  generateTrendTopics,
  skipTopic,
  updateTopicStatus,
} from "../../../lib/api/services"
import type { TopicResponse } from "../../../lib/api/types"

interface RecommendationCardsProps {
  onAddToCalendar: (topic: TopicResponse, date: string) => void
}

const urgencyConfig = {
  urgent: { label: "긴급", icon: Flame, color: "text-red-500", bg: "bg-red-500/20", border: "border-red-500/50" },
  normal: { label: "일반", icon: TrendingUp, color: "text-blue-500", bg: "bg-blue-500/20", border: "border-blue-500/50" },
  evergreen: { label: "상시", icon: Clock, color: "text-green-500", bg: "bg-green-500/20", border: "border-green-500/50" },
}

const topicTypeConfig = {
  channel: { label: "채널 맞춤", icon: User, color: "text-purple-500", bg: "bg-purple-500/20" },
  trend: { label: "트렌드", icon: Zap, color: "text-orange-500", bg: "bg-orange-500/20" },
}

export function RecommendationCards({ onAddToCalendar }: RecommendationCardsProps) {
  const [channelTopics, setChannelTopics] = useState<TopicResponse[]>([])
  const [trendTopics, setTrendTopics] = useState<TopicResponse[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDates, setSelectedDates] = useState<Record<string, string>>({})
  const [addedItems, setAddedItems] = useState<Set<string>>(new Set())
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const hasCalledRef = useRef(false)

  const loadTopics = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const status = await getTopicsStatus()

      // 트렌드 추천이 없거나 만료된 경우 생성
      if (!status.trend_exists || status.trend_expired) {
        setIsGenerating(true)
        const result = await generateTrendTopics()
        if (!result.success) {
          setError(result.message || "추천 생성에 실패했습니다.")
          setIsGenerating(false)
          setIsLoading(false)
          return
        }
        setIsGenerating(false)
      }

      // 전체 주제 조회
      const data = await getTopics()
      setChannelTopics(data.channel_topics)
      setTrendTopics(data.trend_topics)

    } catch (err: any) {
      console.error("추천 로드 실패:", err)
      if (err.response?.status === 404) {
        setError("연결된 YouTube 채널이 없습니다.")
      } else {
        setError("추천을 불러오는데 실패했습니다.")
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleRefreshTrend = async () => {
    try {
      setIsGenerating(true)
      setError(null)
      const result = await generateTrendTopics()
      if (result.success) {
        setTrendTopics(result.topics)
        // 새로고침하면 추가 상태 초기화
        setAddedItems(new Set())
        setSelectedDates({})
      } else {
        setError(result.message || "추천 생성에 실패했습니다.")
      }
    } catch (err) {
      setError("추천 새로고침에 실패했습니다.")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSkipTopic = async (topic: TopicResponse) => {
    try {
      const result = await skipTopic(topic.topic_type, topic.id)

      if (topic.topic_type === 'channel') {
        setChannelTopics(prev => {
          const filtered = prev.filter(t => t.id !== topic.id)
          return result.new_topic ? [...filtered, result.new_topic] : filtered
        })
      } else {
        setTrendTopics(prev => {
          const filtered = prev.filter(t => t.id !== topic.id)
          return result.new_topic ? [...filtered, result.new_topic] : filtered
        })
      }
    } catch (err) {
      console.error("건너뛰기 실패:", err)
    }
  }

  const handleAddToCalendar = async (topic: TopicResponse) => {
    const date = selectedDates[topic.id]
    if (!date) return

    try {
      // 상태를 confirmed로 변경
      await updateTopicStatus(topic.topic_type, topic.id, {
        status: 'confirmed',
        scheduled_date: date,
      })

      onAddToCalendar(topic, date)
      setAddedItems(prev => new Set(prev).add(topic.id))
    } catch (err) {
      console.error("캘린더 추가 실패:", err)
    }
  }

  useEffect(() => {
    if (hasCalledRef.current) return
    hasCalledRef.current = true
    loadTopics()
  }, [])

  const allTopics = [...channelTopics, ...trendTopics]

  // 오늘 날짜 (최소 선택 가능 날짜)
  const today = new Date().toISOString().split('T')[0]

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            AI 추천 주제
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefreshTrend}
            disabled={isGenerating}
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${isGenerating ? 'animate-spin' : ''}`} />
            트렌드 새로고침
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          채널 맞춤 추천과 트렌드 기반 추천입니다. 날짜를 선택하고 캘린더에 추가하세요.
        </p>
      </CardHeader>
      <CardContent>
        {/* 로딩 상태 */}
        {(isLoading || isGenerating) && (
          <div className="flex items-center justify-center py-8 gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
            <p className="text-muted-foreground">
              {isGenerating ? "트렌드 분석 중..." : "추천 불러오는 중..."}
            </p>
          </div>
        )}

        {/* 에러 상태 */}
        {!isLoading && !isGenerating && error && (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <p className="text-muted-foreground text-sm">{error}</p>
            <Button variant="outline" size="sm" onClick={loadTopics}>
              다시 시도
            </Button>
          </div>
        )}

        {/* 추천 카드 목록 */}
        {!isLoading && !isGenerating && !error && (
          <ScrollArea className="w-full">
            <div className="flex gap-4 pb-4">
              {allTopics.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 w-full gap-3">
                  <Sparkles className="w-8 h-8 text-muted-foreground" />
                  <p className="text-muted-foreground">추천 주제가 없습니다</p>
                  <Button variant="outline" size="sm" onClick={handleRefreshTrend}>
                    추천 생성하기
                  </Button>
                </div>
              ) : (
                allTopics.map((topic) => {
                  const urgency = urgencyConfig[topic.urgency] || urgencyConfig.normal
                  const typeConfig = topicTypeConfig[topic.topic_type]
                  const TypeIcon = typeConfig.icon
                  const UrgencyIcon = urgency.icon
                  const isAdded = addedItems.has(topic.id)
                  const isExpanded = expandedId === topic.id

                  return (
                    <div
                      key={topic.id}
                      onClick={() => setExpandedId(isExpanded ? null : topic.id)}
                      className={`flex-shrink-0 w-[280px] p-4 rounded-xl border cursor-pointer transition-all ${urgency.border} ${urgency.bg} ${
                        isAdded ? 'opacity-50' : 'hover:shadow-lg'
                      } ${isExpanded ? 'ring-2 ring-primary' : ''}`}
                    >
                      {/* 헤더 */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className={`w-8 h-8 rounded-lg ${typeConfig.bg} flex items-center justify-center`}>
                            <TypeIcon className={`w-4 h-4 ${typeConfig.color}`} />
                          </div>
                          <Badge variant="outline" className={typeConfig.color}>
                            {typeConfig.label}
                          </Badge>
                          <Badge variant="outline" className={urgency.color}>
                            <UrgencyIcon className="w-3 h-3 mr-1" />
                            {urgency.label}
                          </Badge>
                        </div>
                        {/* 건너뛰기 버튼 */}
                        {!isAdded && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleSkipTopic(topic)
                            }}
                          >
                            <RefreshCw className="w-4 h-4" />
                          </Button>
                        )}
                      </div>

                      {/* 추가됨 표시 */}
                      {isAdded && (
                        <Badge variant="secondary" className="mb-2 bg-green-500/20 text-green-500">
                          캘린더에 추가됨
                        </Badge>
                      )}

                      {/* 제목 */}
                      <h3 className="font-semibold text-foreground mb-3 line-clamp-2">
                        {topic.title}
                      </h3>

                      {/* 콘텐츠 접근 방식 (펼쳐졌을 때만) */}
                      {isExpanded && topic.content_angles && topic.content_angles.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-3 animate-in fade-in slide-in-from-top-2 duration-200">
                          {topic.content_angles.slice(0, 3).map((angle, i) => (
                            <Badge key={i} variant="secondary" className="text-xs">
                              {angle}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {/* 날짜 선택 + 추가 버튼 */}
                      {!isAdded && (
                        <div className="flex gap-2 mt-auto" onClick={(e) => e.stopPropagation()}>
                          <div className="relative flex-1">
                            <Calendar className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                            <input
                              type="date"
                              min={today}
                              value={selectedDates[topic.id] || ''}
                              onChange={(e) =>
                                setSelectedDates(prev => ({ ...prev, [topic.id]: e.target.value }))
                              }
                              className="w-full h-9 pl-8 pr-2 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                            />
                          </div>
                          <Button
                            size="sm"
                            disabled={!selectedDates[topic.id]}
                            onClick={() => handleAddToCalendar(topic)}
                          >
                            <Plus className="w-4 h-4 mr-1" />
                            추가
                          </Button>
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
            <ScrollBar orientation="horizontal" />
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}
