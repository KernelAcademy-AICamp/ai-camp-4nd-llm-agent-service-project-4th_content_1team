"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Badge } from "../../../components/ui/badge"
import { Button } from "../../../components/ui/button"
import { ScrollArea } from "../../../components/ui/scroll-area"
import {
  Bell,
  Newspaper,
  TrendingUp,
  ExternalLink,
  Clock,
  Sparkles,
  Flame,
  Zap,
  ChevronRight,
  RefreshCw
} from "lucide-react"
import { Link } from "react-router-dom"

interface ContentTopic {
  id: number
  title: string
  reason: string
  type: string
  week: number
  confirmed?: boolean
}

interface NewsUpdate {
  id: number
  title: string
  source: string
  time: string
  url: string
  isNew?: boolean
}

interface TrendUpdate {
  id: number
  keyword: string
  change: string
  isUp: boolean
}

interface ConfirmedTopicsPanelProps {
  confirmedTopics: ContentTopic[]
}

const topicNewsData: Record<string, NewsUpdate[]> = {
  "2026 게임 트렌드 예측": [
    { id: 1, title: "2026년 게임 산업, AI와 클라우드 게이밍이 주도할 것", source: "게임메카", time: "2시간 전", url: "#", isNew: true },
    { id: 2, title: "닌텐도 신형 콘솔 발표 임박, 업계 판도 변화 예고", source: "인벤", time: "5시간 전", url: "#", isNew: true },
    { id: 3, title: "2026년 기대작 게임 20선 발표", source: "게임동아", time: "1일 전", url: "#" },
  ],
  "신작 게임 리뷰": [
    { id: 1, title: "GTA 6 출시일 공식 발표, 예약 판매 시작", source: "게임인사이트", time: "30분 전", url: "#", isNew: true },
    { id: 2, title: "엘든링 DLC 새로운 보스 공개", source: "게임샷", time: "3시간 전", url: "#", isNew: true },
    { id: 3, title: "2026년 1월 출시 예정 게임 총정리", source: "게임메카", time: "6시간 전", url: "#" },
  ],
  "게임 초보자 가이드": [
    { id: 1, title: "게임 입문자를 위한 PC 조립 가이드 2026", source: "PC조선", time: "1시간 전", url: "#", isNew: true },
    { id: 2, title: "초보자도 쉽게 배우는 FPS 게임 조작법", source: "게임포커스", time: "4시간 전", url: "#" },
    { id: 3, title: "새해 게임 입문하기 좋은 장르별 추천작", source: "게임동아", time: "1일 전", url: "#" },
  ],
  "e스포츠 대회 분석": [
    { id: 1, title: "LCK 2026 스프링 시즌 일정 확정", source: "게임인사이트", time: "1시간 전", url: "#", isNew: true },
    { id: 2, title: "T1 페이커, 새 시즌 포부 밝혀", source: "인벤", time: "2시간 전", url: "#", isNew: true },
    { id: 3, title: "발로란트 챔피언스 투어 2026 정보 공개", source: "게임샷", time: "5시간 전", url: "#" },
  ],
  "default": [
    { id: 1, title: "관련 최신 뉴스를 불러오는 중...", source: "로딩", time: "방금", url: "#" },
  ]
}

const topicTrendData: Record<string, TrendUpdate[]> = {
  "2026 게임 트렌드 예측": [
    { id: 1, keyword: "2026 게임", change: "+340%", isUp: true },
    { id: 2, keyword: "게임 트렌드", change: "+180%", isUp: true },
    { id: 3, keyword: "AI 게임", change: "+520%", isUp: true },
  ],
  "신작 게임 리뷰": [
    { id: 1, keyword: "GTA 6", change: "+890%", isUp: true },
    { id: 2, keyword: "엘든링 DLC", change: "+450%", isUp: true },
    { id: 3, keyword: "신작 게임", change: "+210%", isUp: true },
  ],
  "게임 초보자 가이드": [
    { id: 1, keyword: "게임 입문", change: "+120%", isUp: true },
    { id: 2, keyword: "게임 시작하기", change: "+85%", isUp: true },
    { id: 3, keyword: "초보자 추천 게임", change: "+95%", isUp: true },
  ],
  "e스포츠 대회 분석": [
    { id: 1, keyword: "LCK 2026", change: "+670%", isUp: true },
    { id: 2, keyword: "T1 페이커", change: "+320%", isUp: true },
    { id: 3, keyword: "e스포츠 일정", change: "+180%", isUp: true },
  ],
  "default": [
    { id: 1, keyword: "검색 트렌드", change: "+0%", isUp: true },
  ]
}

const typeIcons = {
  trend: { icon: TrendingUp, color: "text-chart-1", bg: "bg-chart-1/20" },
  hot: { icon: Flame, color: "text-chart-3", bg: "bg-chart-3/20" },
  evergreen: { icon: Sparkles, color: "text-chart-2", bg: "bg-chart-2/20" },
  event: { icon: Zap, color: "text-chart-4", bg: "bg-chart-4/20" },
  seasonal: { icon: Sparkles, color: "text-chart-5", bg: "bg-chart-5/20" },
}

export function ConfirmedTopicsPanel({ confirmedTopics }: ConfirmedTopicsPanelProps) {
  const [selectedTopic, setSelectedTopic] = useState<ContentTopic | null>(
    confirmedTopics.length > 0 ? confirmedTopics[0] : null
  )
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(new Date())

  useEffect(() => {
    if (confirmedTopics.length > 0 && !selectedTopic) {
      setSelectedTopic(confirmedTopics[0])
    }
  }, [confirmedTopics, selectedTopic])

  const newsUpdates = selectedTopic
    ? topicNewsData[selectedTopic.title] || topicNewsData["default"]
    : []

  const trendUpdates = selectedTopic
    ? topicTrendData[selectedTopic.title] || topicTrendData["default"]
    : []

  const handleRefresh = () => {
    setIsRefreshing(true)
    setTimeout(() => {
      setIsRefreshing(false)
      setLastUpdated(new Date())
    }, 1000)
  }

  if (confirmedTopics.length === 0) {
    return (
      <Card className="border-border/50 bg-card/50 backdrop-blur h-full">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary" />
            확정된 주제 업데이트
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mb-4">
              <Sparkles className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="font-medium text-foreground mb-2">아직 확정된 주제가 없습니다</h3>
            <p className="text-sm text-muted-foreground max-w-[200px]">
              캘린더에서 주제를 확정하면 관련 뉴스와 트렌드를 실시간으로 확인할 수 있습니다
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary" />
            확정된 주제 업데이트
            <Badge variant="secondary" className="ml-1">{confirmedTopics.length}</Badge>
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          마지막 업데이트: {lastUpdated.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Topic Selector */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {confirmedTopics.map((topic) => {
            const typeInfo = typeIcons[topic.type as keyof typeof typeIcons]
            const Icon = typeInfo.icon
            return (
              <button
                key={topic.id}
                onClick={() => setSelectedTopic(topic)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-all whitespace-nowrap ${selectedTopic?.id === topic.id
                  ? "border-primary bg-primary/10"
                  : "border-border/50 hover:border-border hover:bg-muted/50"
                  }`}
              >
                <Icon className={`w-4 h-4 ${typeInfo.color}`} />
                <span className="text-sm font-medium truncate max-w-[120px]">{topic.title}</span>
              </button>
            )
          })}
        </div>

        {selectedTopic && (
          <>
            {/* News Updates */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Newspaper className="w-4 h-4 text-muted-foreground" />
                <h4 className="text-sm font-semibold">관련 뉴스</h4>
              </div>
              <ScrollArea className="h-[200px]">
                <div className="space-y-2 pr-4">
                  {newsUpdates.map((news) => (
                    <a
                      key={news.id}
                      href={news.url}
                      className="block p-3 rounded-lg border border-border/50 hover:border-primary/50 hover:bg-muted/30 transition-all group"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            {news.isNew && (
                              <Badge variant="default" className="bg-destructive text-destructive-foreground text-[10px] px-1.5 py-0">
                                NEW
                              </Badge>
                            )}
                            <span className="text-xs text-muted-foreground">{news.source}</span>
                          </div>
                          <p className="text-sm font-medium line-clamp-2 group-hover:text-primary transition-colors">
                            {news.title}
                          </p>
                          <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                            <Clock className="w-3 h-3" />
                            {news.time}
                          </div>
                        </div>
                        <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-primary flex-shrink-0" />
                      </div>
                    </a>
                  ))}
                </div>
              </ScrollArea>
            </div>

            {/* Trend Updates */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-muted-foreground" />
                <h4 className="text-sm font-semibold">검색 트렌드</h4>
              </div>
              <div className="grid gap-2">
                {trendUpdates.map((trend) => (
                  <div
                    key={trend.id}
                    className="flex items-center justify-between p-2 rounded-lg bg-muted/30"
                  >
                    <span className="text-sm font-medium">{trend.keyword}</span>
                    <Badge
                      variant="secondary"
                      className={trend.isUp ? "bg-accent/20 text-accent" : "bg-destructive/20 text-destructive"}
                    >
                      {trend.isUp ? "↑" : "↓"} {trend.change}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Action */}
            <Link to={`/script?topic=${encodeURIComponent(selectedTopic.title)}`}>
              <Button className="w-full mt-2 bg-transparent" variant="outline">
                <span>스크립트 작성하기</span>
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </>
        )}
      </CardContent>
    </Card>
  )
}
