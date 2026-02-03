"use client"

import { useEffect, useState, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Badge } from "../../../components/ui/badge"
import { Button } from "../../../components/ui/button"
import { ScrollArea, ScrollBar } from "../../../components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../../components/ui/select"
import {
  Sparkles,
  Loader2,
  RefreshCw,
  Plus,
  Flame,
  Clock,
  TrendingUp,
} from "lucide-react"
import {
  getRecommendations,
  generateRecommendations,
  getRecommendationStatus,
} from "../../../lib/api/services"
import type { RecommendationItem } from "../../../lib/api/types"

interface RecommendationCardsProps {
  onAddToCalendar: (recommendation: RecommendationItem, week: number) => void
}

const urgencyConfig = {
  urgent: { label: "긴급", icon: Flame, color: "text-red-500", bg: "bg-red-500/20", border: "border-red-500/50" },
  normal: { label: "일반", icon: TrendingUp, color: "text-blue-500", bg: "bg-blue-500/20", border: "border-blue-500/50" },
  evergreen: { label: "상시", icon: Clock, color: "text-green-500", bg: "bg-green-500/20", border: "border-green-500/50" },
}

export function RecommendationCards({ onAddToCalendar }: RecommendationCardsProps) {
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedWeeks, setSelectedWeeks] = useState<Record<number, string>>({})
  const [addedItems, setAddedItems] = useState<Set<number>>(new Set())

  // StrictMode 중복 호출 방지
  const hasCalledRef = useRef(false)

  const loadRecommendations = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const status = await getRecommendationStatus()

      if (!status.exists || status.is_expired) {
        setIsGenerating(true)
        const generateResult = await generateRecommendations()

        if (generateResult.success && generateResult.data) {
          setRecommendations(generateResult.data.recommendations)
        } else {
          setError(generateResult.message || "추천 생성에 실패했습니다.")
        }
        setIsGenerating(false)
      } else {
        const data = await getRecommendations()
        setRecommendations(data.recommendations)
      }
    } catch (err: any) {
      console.error("추천 로드 실패:", err)
      if (err.response?.status === 404) {
        try {
          setIsGenerating(true)
          const generateResult = await generateRecommendations()
          if (generateResult.success && generateResult.data) {
            setRecommendations(generateResult.data.recommendations)
          } else {
            setError(generateResult.message || "추천 생성에 실패했습니다.")
          }
        } catch (genErr: any) {
          setError("추천 생성에 실패했습니다. 페르소나가 먼저 생성되어야 합니다.")
        } finally {
          setIsGenerating(false)
        }
      } else {
        setError("추천을 불러오는데 실패했습니다.")
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleRefresh = async () => {
    try {
      setIsGenerating(true)
      setError(null)
      setAddedItems(new Set())
      setSelectedWeeks({})
      const generateResult = await generateRecommendations()
      if (generateResult.success && generateResult.data) {
        setRecommendations(generateResult.data.recommendations)
      } else {
        setError(generateResult.message || "추천 생성에 실패했습니다.")
      }
    } catch (err) {
      setError("추천 새로고침에 실패했습니다.")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleAddToCalendar = (rec: RecommendationItem, index: number) => {
    const week = parseInt(selectedWeeks[index] || "1")
    onAddToCalendar(rec, week)
    setAddedItems(prev => new Set(prev).add(index))
  }

  useEffect(() => {
    if (hasCalledRef.current) return
    hasCalledRef.current = true
    loadRecommendations()
  }, [])

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
            onClick={handleRefresh}
            disabled={isGenerating}
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${isGenerating ? 'animate-spin' : ''}`} />
            새로고침
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          채널 특성과 트렌드를 분석하여 추천된 콘텐츠입니다. 원하는 주제를 캘린더에 추가하세요.
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
            <Button variant="outline" size="sm" onClick={loadRecommendations}>
              다시 시도
            </Button>
          </div>
        )}

        {/* 추천 카드 목록 */}
        {!isLoading && !isGenerating && !error && (
          <ScrollArea className="w-full">
            <div className="flex gap-4 pb-4">
              {recommendations.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 w-full gap-3">
                  <Sparkles className="w-8 h-8 text-muted-foreground" />
                  <p className="text-muted-foreground">추천 콘텐츠가 없습니다</p>
                  <Button variant="outline" size="sm" onClick={handleRefresh}>
                    추천 생성하기
                  </Button>
                </div>
              ) : (
                recommendations.map((rec, index) => {
                  const urgency = urgencyConfig[rec.urgency] || urgencyConfig.normal
                  const UrgencyIcon = urgency.icon
                  const isAdded = addedItems.has(index)

                  return (
                    <div
                      key={index}
                      className={`flex-shrink-0 w-[320px] p-4 rounded-xl border ${urgency.border} ${urgency.bg} transition-all ${
                        isAdded ? 'opacity-50' : 'hover:shadow-lg'
                      }`}
                    >
                      {/* 헤더 */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className={`w-8 h-8 rounded-lg ${urgency.bg} flex items-center justify-center`}>
                            <UrgencyIcon className={`w-4 h-4 ${urgency.color}`} />
                          </div>
                          <Badge variant="outline" className={urgency.color}>
                            {urgency.label}
                          </Badge>
                        </div>
                        {isAdded && (
                          <Badge variant="secondary" className="bg-green-500/20 text-green-500">
                            추가됨
                          </Badge>
                        )}
                      </div>

                      {/* 제목 */}
                      <h3 className="font-semibold text-foreground mb-2 line-clamp-2">
                        {rec.title}
                      </h3>

                      {/* 트렌드 근거 */}
                      <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                        {rec.trend_basis}
                      </p>

                      {/* 토픽 태그 */}
                      <div className="flex flex-wrap gap-1 mb-3">
                        <Badge variant="secondary" className="text-xs">
                          {rec.based_on_topic}
                        </Badge>
                        {rec.content_angles?.slice(0, 2).map((angle, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {angle}
                          </Badge>
                        ))}
                      </div>

                      {/* 주차 선택 + 추가 버튼 */}
                      {!isAdded && (
                        <div className="flex gap-2 mt-auto">
                          <Select
                            value={selectedWeeks[index] || "1"}
                            onValueChange={(value) =>
                              setSelectedWeeks(prev => ({ ...prev, [index]: value }))
                            }
                          >
                            <SelectTrigger className="w-[100px]">
                              <SelectValue placeholder="주차" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="1">1주차</SelectItem>
                              <SelectItem value="2">2주차</SelectItem>
                              <SelectItem value="3">3주차</SelectItem>
                              <SelectItem value="4">4주차</SelectItem>
                            </SelectContent>
                          </Select>
                          <Button
                            size="sm"
                            className="flex-1"
                            onClick={() => handleAddToCalendar(rec, index)}
                          >
                            <Plus className="w-4 h-4 mr-1" />
                            캘린더에 추가
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
