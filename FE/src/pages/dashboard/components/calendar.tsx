"use client"

import { useState, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Button } from "../../../components/ui/button"
import { Badge } from "../../../components/ui/badge"
import { ChevronLeft, ChevronRight, Sparkles, TrendingUp, Flame, Zap, Check, X, RefreshCw } from "lucide-react"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../../../components/ui/popover"
import { Link } from "react-router-dom"

interface ContentTopic {
  id: number
  title: string
  reason: string
  type: string
  week: number
  confirmed?: boolean
}

interface ContentCalendarProps {
  weeklyUploads: number
  onTopicConfirm?: (topic: ContentTopic) => void
  confirmedTopics?: ContentTopic[]
}

const initialContentTopics: ContentTopic[] = [
  {
    id: 1,
    title: "2026 게임 트렌드 예측",
    reason: "연초 트렌드 예측 콘텐츠가 높은 조회수를 기록합니다. 검색량 +340% 증가",
    type: "trend",
    week: 1
  },
  {
    id: 2,
    title: "신작 게임 리뷰",
    reason: "1월 출시 예정 대작 게임들에 대한 관심이 급증하고 있습니다",
    type: "hot",
    week: 1
  },
  {
    id: 3,
    title: "게임 초보자 가이드",
    reason: "새해를 맞아 새로운 취미를 찾는 시청자가 많습니다. 에버그린 콘텐츠로 장기적 조회수 확보",
    type: "evergreen",
    week: 2
  },
  {
    id: 4,
    title: "e스포츠 대회 분석",
    reason: "1월 주요 e스포츠 대회 시즌 시작. 관련 검색량 급증 예상",
    type: "event",
    week: 2
  },
  {
    id: 5,
    title: "게임 할인 정보 총정리",
    reason: "설날 연휴 할인 시즌에 맞춘 실용 콘텐츠. 높은 저장률 예상",
    type: "trend",
    week: 3
  },
  {
    id: 6,
    title: "멀티플레이 게임 추천",
    reason: "설날 연휴 시즌, 친구/가족과 함께하는 게임 수요 증가",
    type: "seasonal",
    week: 3
  },
  {
    id: 7,
    title: "인디게임 발굴 시리즈",
    reason: "언더레이더 인디게임에 대한 관심 증가 추세",
    type: "hot",
    week: 4
  },
  {
    id: 8,
    title: "게임 세팅 최적화",
    reason: "새해 PC 업그레이드 시즌, 최적화 관련 검색 증가",
    type: "evergreen",
    week: 4
  },
]

const alternativeTopics: Record<number, ContentTopic[]> = {
  1: [
    { id: 101, title: "2026 기대작 게임 TOP 10", reason: "새해 기대작 목록은 항상 높은 관심을 받습니다", type: "trend", week: 1 },
    { id: 102, title: "게임 유튜버가 알려주는 꿀팁", reason: "실용적인 팁 콘텐츠는 저장률이 높습니다", type: "evergreen", week: 1 },
  ],
  2: [
    { id: 201, title: "스팀 베스트셀러 분석", reason: "스팀 인기 게임 분석은 꾸준한 검색량을 보입니다", type: "hot", week: 1 },
    { id: 202, title: "게임 스트리머 추천", reason: "커뮤니티 관련 콘텐츠로 구독자 확보 가능", type: "trend", week: 1 },
  ],
  3: [
    { id: 301, title: "무료 게임 BEST 5", reason: "무료 게임 추천은 항상 높은 클릭률을 보입니다", type: "trend", week: 2 },
    { id: 302, title: "게임 입문 가이드 2026", reason: "새해 새로운 시작을 원하는 시청자 타겟", type: "evergreen", week: 2 },
  ],
  4: [
    { id: 401, title: "프로게이머 인터뷰", reason: "e스포츠 시즌과 연계한 콘텐츠", type: "event", week: 2 },
    { id: 402, title: "게임 대회 하이라이트", reason: "대회 시즌 관련 편집 콘텐츠 수요 증가", type: "event", week: 2 },
  ],
  5: [
    { id: 501, title: "할인 게임 숨은 명작", reason: "세일 시즌 숨겨진 보석 찾기 콘텐츠", type: "trend", week: 3 },
    { id: 502, title: "게임 번들 분석", reason: "번들 상품 비교 분석 콘텐츠", type: "trend", week: 3 },
  ],
  6: [
    { id: 601, title: "파티 게임 추천", reason: "연휴 시즌 가족/친구 모임용 게임", type: "seasonal", week: 3 },
    { id: 602, title: "협동 게임 BEST", reason: "함께하는 게임 수요 증가 시즌", type: "seasonal", week: 3 },
  ],
  7: [
    { id: 701, title: "숨겨진 명작 인디게임", reason: "인디게임 팬덤 타겟 콘텐츠", type: "hot", week: 4 },
    { id: 702, title: "인디게임 개발자 인터뷰", reason: "스토리텔링 콘텐츠로 구독자 충성도 향상", type: "hot", week: 4 },
  ],
  8: [
    { id: 801, title: "저사양 PC 게임 추천", reason: "저사양 관련 검색량 꾸준", type: "evergreen", week: 4 },
    { id: 802, title: "게임 녹화 세팅 가이드", reason: "크리에이터 지망생 타겟 콘텐츠", type: "evergreen", week: 4 },
  ],
}

const typeIcons = {
  trend: { icon: TrendingUp, color: "text-chart-1", bg: "bg-chart-1/20", bgSolid: "bg-chart-1" },
  hot: { icon: Flame, color: "text-chart-3", bg: "bg-chart-3/20", bgSolid: "bg-chart-3" },
  evergreen: { icon: Sparkles, color: "text-chart-2", bg: "bg-chart-2/20", bgSolid: "bg-chart-2" },
  event: { icon: Zap, color: "text-chart-4", bg: "bg-chart-4/20", bgSolid: "bg-chart-4" },
  seasonal: { icon: Sparkles, color: "text-chart-5", bg: "bg-chart-5/20", bgSolid: "bg-chart-5" },
}

const weekDays = ["일", "월", "화", "수", "목", "금", "토"]

export function ContentCalendar({ weeklyUploads, onTopicConfirm, confirmedTopics = [] }: ContentCalendarProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date(2026, 0))
  const [contentTopics, setContentTopics] = useState<ContentTopic[]>(initialContentTopics)
  const [openPopoverId, setOpenPopoverId] = useState<number | null>(null)
  const [replacementIndex, setReplacementIndex] = useState<Record<number, number>>({})

  const filteredTopics = useMemo(() => {
    const topicsPerWeek = weeklyUploads
    const result: ContentTopic[] = []

    for (let week = 1; week <= 4; week++) {
      const weekTopics = contentTopics.filter(t => t.week === week).slice(0, topicsPerWeek)
      result.push(...weekTopics)
    }

    return result
  }, [weeklyUploads, contentTopics])

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

  const getWeekNumber = (day: number) => {
    return Math.ceil(day / 7)
  }

  const getTopicsForDay = (day: number) => {
    const week = getWeekNumber(day)
    const weekTopics = filteredTopics.filter(t => t.week === week)
    const dayOfWeek = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day).getDay()

    if (dayOfWeek === 0 || dayOfWeek === 6) {
      const index = dayOfWeek === 6 ? 0 : 1
      if (weekTopics[index]) {
        return [weekTopics[index]]
      }
    }

    if (dayOfWeek === 3 && weekTopics.length > 2) {
      return [weekTopics[2]]
    }

    return []
  }

  const handleConfirmTopic = (topic: ContentTopic) => {
    const confirmedTopic = { ...topic, confirmed: true }
    setContentTopics(prev =>
      prev.map(t => t.id === topic.id ? confirmedTopic : t)
    )
    onTopicConfirm?.(confirmedTopic)
    setOpenPopoverId(null)
  }

  const handleDiscardTopic = (topic: ContentTopic) => {
    const alternatives = alternativeTopics[topic.id] || []
    const currentIndex = replacementIndex[topic.id] || 0
    const nextIndex = (currentIndex + 1) % alternatives.length

    if (alternatives.length > 0) {
      const replacement = alternatives[currentIndex]
      setContentTopics(prev =>
        prev.map(t => t.id === topic.id ? { ...replacement, id: topic.id, week: topic.week } : t)
      )
      setReplacementIndex(prev => ({ ...prev, [topic.id]: nextIndex }))
    }
  }

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))
  }

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))
  }

  const isTopicConfirmed = (topicId: number) => {
    return confirmedTopics.some(t => t.id === topicId) || contentTopics.find(t => t.id === topicId)?.confirmed
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
                        const typeInfo = typeIcons[topic.type as keyof typeof typeIcons]
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
                                      <p className="text-xs text-muted-foreground capitalize">{topic.type} 콘텐츠</p>
                                    </div>
                                    {confirmed && (
                                      <Badge variant="default" className="bg-accent text-accent-foreground text-xs">
                                        확정됨
                                      </Badge>
                                    )}
                                  </div>
                                </div>

                                {/* Reason */}
                                <div className="bg-muted/50 rounded-lg p-3">
                                  <p className="text-xs font-medium text-muted-foreground mb-1">추천 이유</p>
                                  <p className="text-sm">{topic.reason}</p>
                                </div>

                                {/* Actions */}
                                {!confirmed ? (
                                  <div className="flex gap-2">
                                    <Button
                                      size="sm"
                                      className="flex-1 bg-accent hover:bg-accent/90"
                                      onClick={() => handleConfirmTopic(topic)}
                                    >
                                      <Check className="w-4 h-4 mr-1" />
                                      주제 확정하기
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="flex-1 bg-transparent"
                                      onClick={() => handleDiscardTopic(topic)}
                                    >
                                      <RefreshCw className="w-4 h-4 mr-1" />
                                      다른 주제 추천
                                    </Button>
                                  </div>
                                ) : (
                                  <div className="flex gap-2">
                                    <Link to={`/script?topic=${encodeURIComponent(topic.title)}`} className="flex-1">
                                      <Button size="sm" className="w-full bg-primary hover:bg-primary/90">
                                        스크립트 작성하기
                                      </Button>
                                    </Link>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => {
                                        setContentTopics(prev =>
                                          prev.map(t => t.id === topic.id ? { ...t, confirmed: false } : t)
                                        )
                                      }}
                                    >
                                      <X className="w-4 h-4" />
                                    </Button>
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
          {Object.entries(typeIcons).map(([key, value]) => {
            const Icon = value.icon
            const labels: Record<string, string> = {
              trend: "트렌드",
              hot: "인기",
              evergreen: "에버그린",
              event: "이벤트",
              seasonal: "시즌"
            }
            return (
              <div key={key} className="flex items-center gap-2 text-sm">
                <div className={`w-6 h-6 rounded flex items-center justify-center ${value.bg}`}>
                  <Icon className={`w-3 h-3 ${value.color}`} />
                </div>
                <span className="text-muted-foreground">{labels[key]}</span>
              </div>
            )
          })}
          <div className="flex items-center gap-2 text-sm ml-auto">
            <div className="w-6 h-6 rounded flex items-center justify-center bg-accent">
              <Check className="w-3 h-3 text-white" />
            </div>
            <span className="text-muted-foreground">확정됨</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
