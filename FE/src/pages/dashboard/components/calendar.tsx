"use client"

import { useState, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Button } from "../../../components/ui/button"
import { Badge } from "../../../components/ui/badge"
import { ChevronLeft, ChevronRight, Sparkles, TrendingUp, Flame, Zap, Check, User } from "lucide-react"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../../../components/ui/popover"
import { Link } from "react-router-dom"

interface ContentTopic {
  id: string
  title: string
  reason: string
  type: string
  date: string  // "2024-02-15" 형식
  week?: number
  confirmed?: boolean
  based_on_topic?: string
  trend_basis?: string
  recommendation_reason?: string
  content_angles?: string[]
  thumbnail_idea?: string
  urgency?: string
  search_keywords?: string[]
  topic_type?: 'channel' | 'trend'
}

interface ContentCalendarProps {
  weeklyUploads: number
  onTopicConfirm?: (topic: ContentTopic) => void
  confirmedTopics?: ContentTopic[]
  externalTopics?: ContentTopic[]
}

const typeIcons = {
  trend: { icon: TrendingUp, color: "text-chart-1", bg: "bg-chart-1/20", bgSolid: "bg-chart-1" },
  hot: { icon: Flame, color: "text-chart-3", bg: "bg-chart-3/20", bgSolid: "bg-chart-3" },
  evergreen: { icon: Sparkles, color: "text-chart-2", bg: "bg-chart-2/20", bgSolid: "bg-chart-2" },
  event: { icon: Zap, color: "text-chart-4", bg: "bg-chart-4/20", bgSolid: "bg-chart-4" },
  seasonal: { icon: Sparkles, color: "text-chart-5", bg: "bg-chart-5/20", bgSolid: "bg-chart-5" },
  channel: { icon: User, color: "text-purple-500", bg: "bg-purple-500/20", bgSolid: "bg-purple-500" },
}

const weekDays = ["일", "월", "화", "수", "목", "금", "토"]

export function ContentCalendar({
  weeklyUploads,
  onTopicConfirm,
  confirmedTopics = [],
  externalTopics = []
}: ContentCalendarProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [openPopoverId, setOpenPopoverId] = useState<string | null>(null)

  const contentTopics = externalTopics

  const calendarDays = useMemo(() => {
    const year = currentMonth.getFullYear()
    const month = currentMonth.getMonth()
    const firstDay = new Date(year, month, 1).getDay()
    const daysInMonth = new Date(year, month + 1, 0).getDate()

    const days: (number | null)[] = []

    for (let i = 0; i < firstDay; i++) {
      days.push(null)
    }

    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i)
    }

    return days
  }, [currentMonth])

  // date 기반으로 해당 날짜의 주제 찾기
  const getTopicsForDay = (day: number) => {
    const year = currentMonth.getFullYear()
    const month = currentMonth.getMonth()
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`

    return contentTopics.filter(t => t.date === dateStr)
  }

  const handleConfirmTopic = (topic: ContentTopic) => {
    const confirmedTopic = { ...topic, confirmed: true }
    onTopicConfirm?.(confirmedTopic)
    setOpenPopoverId(null)
  }

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))
  }

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))
  }

  const isTopicConfirmed = (topicId: string) => {
    return confirmedTopics.some(t => t.id === topicId)
  }

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <CardTitle className="text-xl">콘텐츠 캘린더</CardTitle>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={prevMonth}>
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <span className="text-lg font-semibold min-w-[140px] text-center">
            {currentMonth.getFullYear()}년 {currentMonth.getMonth() + 1}월
          </span>
          <Button variant="outline" size="icon" onClick={nextMonth}>
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Week Days Header */}
        <div className="grid grid-cols-7 gap-1 mb-2">
          {weekDays.map((day) => (
            <div key={day} className="text-center text-sm font-medium text-muted-foreground py-2">
              {day}
            </div>
          ))}
        </div>

        {/* Calendar Grid */}
        <div className="grid grid-cols-7 gap-1">
          {calendarDays.map((day, index) => {
            const topics = day ? getTopicsForDay(day) : []
            return (
              <div
                key={index}
                className={`min-h-[100px] p-2 rounded-lg border ${day ? "border-border/50 bg-muted/20" : "border-transparent"
                  }`}
              >
                {day && (
                  <>
                    <span className={`text-sm ${index % 7 === 0 ? "text-red-400" :
                      index % 7 === 6 ? "text-blue-400" :
                        "text-muted-foreground"
                      }`}>
                      {day}
                    </span>
                    <div className="mt-1 space-y-1">
                      {topics.map((topic) => {
                        // topic_type이 있으면 그걸로, 없으면 type으로
                        const iconKey = topic.topic_type === 'channel' ? 'channel' : (topic.type as keyof typeof typeIcons)
                        const typeInfo = typeIcons[iconKey] || typeIcons.trend
                        const Icon = typeInfo.icon
                        const confirmed = isTopicConfirmed(topic.id)

                        return (
                          <Popover
                            key={topic.id}
                            open={openPopoverId === topic.id}
                            onOpenChange={(open) => setOpenPopoverId(open ? topic.id : null)}
                          >
                            <PopoverTrigger asChild>
                              <Badge
                                variant="secondary"
                                className={`w-full justify-start gap-1 cursor-pointer hover:bg-primary/20 transition-colors text-xs truncate ${confirmed ? `${typeInfo.bgSolid} text-white` : typeInfo.bg
                                  }`}
                              >
                                {confirmed && <Check className="w-3 h-3 flex-shrink-0" />}
                                <Icon className={`w-3 h-3 ${confirmed ? "text-white" : typeInfo.color} flex-shrink-0`} />
                                <span className="truncate">{topic.title}</span>
                              </Badge>
                            </PopoverTrigger>
                            <PopoverContent side="right" className="w-80 p-0" align="start">
                              <div className="p-4 space-y-4">
                                {/* Header */}
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${typeInfo.bg}`}>
                                      <Icon className={`w-4 h-4 ${typeInfo.color}`} />
                                    </div>
                                    <div className="flex-1">
                                      <h4 className="font-semibold text-sm">{topic.title}</h4>
                                      <p className="text-xs text-muted-foreground">
                                        {topic.topic_type === 'channel' ? '채널 맞춤' : '트렌드'} · {topic.based_on_topic || topic.type}
                                      </p>
                                    </div>
                                    {confirmed && (
                                      <Badge variant="default" className="bg-accent text-accent-foreground text-xs">
                                        확정됨
                                      </Badge>
                                    )}
                                  </div>
                                </div>

                                {/* 트렌드 근거 */}
                                {topic.trend_basis && (
                                  <div className="bg-muted/50 rounded-lg p-3">
                                    <p className="text-xs font-medium text-muted-foreground mb-1">트렌드 근거</p>
                                    <p className="text-sm">{topic.trend_basis}</p>
                                  </div>
                                )}

                                {/* 추천 이유 */}
                                {topic.recommendation_reason && (
                                  <div className="bg-primary/10 rounded-lg p-3">
                                    <p className="text-xs font-medium text-primary mb-1">추천 이유</p>
                                    <p className="text-sm">{topic.recommendation_reason}</p>
                                  </div>
                                )}

                                {/* 콘텐츠 관점 */}
                                {topic.content_angles && topic.content_angles.length > 0 && (
                                  <div>
                                    <p className="text-xs font-medium text-muted-foreground mb-2">콘텐츠 관점</p>
                                    <div className="flex flex-wrap gap-1">
                                      {topic.content_angles.map((angle, i) => (
                                        <Badge key={i} variant="outline" className="text-xs">
                                          {angle}
                                        </Badge>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {/* 검색 키워드 */}
                                {topic.search_keywords && topic.search_keywords.length > 0 && (
                                  <div>
                                    <p className="text-xs font-medium text-muted-foreground mb-2">검색 키워드</p>
                                    <div className="flex flex-wrap gap-1">
                                      {topic.search_keywords.map((keyword, i) => (
                                        <Badge key={i} variant="secondary" className="text-xs">
                                          {keyword}
                                        </Badge>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {/* 썸네일 아이디어 */}
                                {topic.thumbnail_idea && (
                                  <div className="bg-muted/30 rounded-lg p-3">
                                    <p className="text-xs font-medium text-muted-foreground mb-1">썸네일 아이디어</p>
                                    <p className="text-sm italic">{topic.thumbnail_idea}</p>
                                  </div>
                                )}

                                {/* 기본 이유 (API 데이터가 없을 때) */}
                                {!topic.trend_basis && !topic.recommendation_reason && topic.reason && (
                                  <div className="bg-muted/50 rounded-lg p-3">
                                    <p className="text-xs font-medium text-muted-foreground mb-1">추천 이유</p>
                                    <p className="text-sm">{topic.reason}</p>
                                  </div>
                                )}

                                {/* Actions */}
                                {!confirmed ? (
                                  <Button
                                    size="sm"
                                    className="w-full bg-accent hover:bg-accent/90"
                                    onClick={() => handleConfirmTopic(topic)}
                                  >
                                    <Check className="w-4 h-4 mr-1" />
                                    주제 확정하기
                                  </Button>
                                ) : (
                                  <div className="flex gap-2">
                                    <Link to={`/script?topic=${encodeURIComponent(topic.title)}&topicId=${topic.id}&topicType=${topic.topic_type || 'trend'}`} className="flex-1">
                                      <Button size="sm" className="w-full bg-primary hover:bg-primary/90">
                                        스크립트 작성하기
                                      </Button>
                                    </Link>
                                  </div>
                                )}
                              </div>
                            </PopoverContent>
                          </Popover>
                        )
                      })}
                    </div>
                  </>
                )}
              </div>
            )
          })}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t border-border/50">
          <div className="flex items-center gap-2 text-sm">
            <div className="w-6 h-6 rounded flex items-center justify-center bg-purple-500/20">
              <User className="w-3 h-3 text-purple-500" />
            </div>
            <span className="text-muted-foreground">채널 맞춤</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <div className="w-6 h-6 rounded flex items-center justify-center bg-chart-3/20">
              <Flame className="w-3 h-3 text-chart-3" />
            </div>
            <span className="text-muted-foreground">트렌드 (긴급)</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <div className="w-6 h-6 rounded flex items-center justify-center bg-chart-1/20">
              <TrendingUp className="w-3 h-3 text-chart-1" />
            </div>
            <span className="text-muted-foreground">트렌드 (일반)</span>
          </div>
          <div className="flex items-center gap-2 text-sm ml-auto">
            <div className="w-6 h-6 rounded flex items-center justify-center bg-accent">
              <Check className="w-3 h-3 text-white" />
            </div>
            <span className="text-muted-foreground">확정됨</span>
          </div>
        </div>

        {/* 주제 없을 때 안내 */}
        {contentTopics.length === 0 && (
          <div className="mt-4 p-4 rounded-lg bg-muted/30 text-center">
            <p className="text-sm text-muted-foreground">
              상단의 AI 추천에서 주제를 선택하여 캘린더에 추가하세요
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
