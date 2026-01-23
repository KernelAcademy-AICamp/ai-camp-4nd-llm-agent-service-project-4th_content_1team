"use client"

import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Badge } from "../../../components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../components/ui/tabs"
import { TrendingUp, Newspaper, ExternalLink, ArrowUpRight, Clock } from "lucide-react"
import { ScrollArea } from "../../../components/ui/scroll-area"

const trendingTopics = [
  { id: 1, title: "엘든링 DLC 출시", change: "+450%", category: "게임" },
  { id: 2, title: "GTA 6 출시일 확정", change: "+380%", category: "게임" },
  { id: 3, title: "스팀 윈터 세일", change: "+220%", category: "할인" },
  { id: 4, title: "PS6 루머", change: "+180%", category: "하드웨어" },
  { id: 5, title: "인디게임 어워드 2026", change: "+150%", category: "이벤트" },
  { id: 6, title: "클라우드 게이밍 비교", change: "+120%", category: "기술" },
]

const newsItems = [
  {
    id: 1,
    title: "닌텐도, 차세대 콘솔 발표 임박",
    source: "게임인사이드",
    time: "2시간 전",
    url: "#"
  },
  {
    id: 2,
    title: "2026년 가장 기대되는 게임 TOP 10",
    source: "게임스팟",
    time: "4시간 전",
    url: "#"
  },
  {
    id: 3,
    title: "e스포츠 시장 규모 2조원 돌파",
    source: "게임동아",
    time: "6시간 전",
    url: "#"
  },
  {
    id: 4,
    title: "AI 기술이 바꾸는 게임 개발의 미래",
    source: "테크크런치",
    time: "8시간 전",
    url: "#"
  },
  {
    id: 5,
    title: "소니, 인디 게임 지원 프로그램 확대",
    source: "게임메카",
    time: "12시간 전",
    url: "#"
  },
]

export function TrendPanel() {
  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur h-full">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl">실시간 인사이트</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Tabs defaultValue="trends" className="w-full">
          <TabsList className="w-full grid grid-cols-2 mx-6 mb-4" style={{ width: 'calc(100% - 48px)' }}>
            <TabsTrigger value="trends" className="gap-2">
              <TrendingUp className="w-4 h-4" />
              트렌드
            </TabsTrigger>
            <TabsTrigger value="news" className="gap-2">
              <Newspaper className="w-4 h-4" />
              뉴스
            </TabsTrigger>
          </TabsList>

          <TabsContent value="trends" className="m-0">
            <ScrollArea className="h-[450px] px-6 pb-6">
              <div className="space-y-3">
                {trendingTopics.map((topic, index) => (
                  <div
                    key={topic.id}
                    className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer"
                  >
                    <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary font-bold text-sm">
                      {index + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground truncate">{topic.title}</p>
                      <Badge variant="secondary" className="text-xs mt-1">
                        {topic.category}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-1 text-accent">
                      <ArrowUpRight className="w-4 h-4" />
                      <span className="text-sm font-medium">{topic.change}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 p-4 rounded-xl bg-primary/10 border border-primary/20">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                    <TrendingUp className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">AI 추천</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {"'GTA 6 출시일 확정' 관련 콘텐츠가 이번 주 가장 높은 관심을 받을 것으로 예상됩니다."}
                    </p>
                  </div>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="news" className="m-0">
            <ScrollArea className="h-[450px] px-6 pb-6">
              <div className="space-y-3">
                {newsItems.map((news) => (
                  <a
                    key={news.id}
                    href={news.url}
                    className="block p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-medium text-foreground group-hover:text-primary transition-colors">
                        {news.title}
                      </h3>
                      <ExternalLink className="w-4 h-4 text-muted-foreground flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <div className="flex items-center gap-2 mt-2 text-sm text-muted-foreground">
                      <span>{news.source}</span>
                      <span className="w-1 h-1 rounded-full bg-muted-foreground" />
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {news.time}
                      </div>
                    </div>
                  </a>
                ))}
              </div>

              <div className="mt-6 p-4 rounded-xl bg-accent/10 border border-accent/20">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center">
                    <Newspaper className="w-5 h-5 text-accent" />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">뉴스 트렌드</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      오늘 게임 관련 뉴스 중 70%가 차세대 콘솔과 관련되어 있습니다.
                    </p>
                  </div>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
