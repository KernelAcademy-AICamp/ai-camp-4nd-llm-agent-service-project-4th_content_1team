"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../components/ui/tabs"
import { Badge } from "../../../components/ui/badge"
import { ExternalLink, Video, FileText, Share2, Bookmark, Globe, Building2, ImageIcon, Clock } from "lucide-react"
import { ScrollArea } from "../../../components/ui/scroll-area"

interface SourceData {
  id: string
  name: string
  icon: string
  articles: {
    id: number
    title: string
    date: string
    excerpt: string
    url: string
  }[]
  images: {
    id: number
    title: string
    type: string
    thumbnail: string
  }[]
}

const sources: SourceData[] = [
  {
    id: "gameinsight",
    name: "게임인사이드",
    icon: "game",
    articles: [
      {
        id: 1,
        title: "2026년 게임 산업 전망 보고서",
        date: "2026.01.15",
        excerpt: "글로벌 게임 시장 규모가 2,500억 달러를 돌파할 것으로 예상되며, 특히 아시아 시장의 성장이 두드러질 전망이다...",
        url: "#"
      },
      {
        id: 2,
        title: "한국 게임 시장 성장률 1위 달성",
        date: "2026.01.14",
        excerpt: "한국 게임 시장이 전년 대비 25% 성장하며 세계 최고 성장률을 기록했다...",
        url: "#"
      }
    ],
    images: [
      {
        id: 1,
        title: "게임 시장 성장 그래프",
        type: "차트",
        thumbnail: "bg-gradient-to-br from-chart-1/30 to-chart-2/30"
      },
      {
        id: 2,
        title: "플랫폼별 점유율 인포그래픽",
        type: "인포그래픽",
        thumbnail: "bg-gradient-to-br from-chart-3/30 to-chart-4/30"
      }
    ]
  },
  {
    id: "techcrunch",
    name: "테크크런치",
    icon: "tech",
    articles: [
      {
        id: 3,
        title: "AI가 바꾸는 게임 개발의 미래",
        date: "2026.01.12",
        excerpt: "대형 게임 스튜디오들이 AI 기술을 적극 도입하면서 게임 개발 비용이 최대 40%까지 절감되고 있다...",
        url: "#"
      },
      {
        id: 4,
        title: "게임 AI NPC 기술의 혁신",
        date: "2026.01.10",
        excerpt: "최신 LLM을 활용한 NPC가 플레이어와 자연스러운 대화를 나눌 수 있게 되었다...",
        url: "#"
      }
    ],
    images: [
      {
        id: 3,
        title: "AI 게임 개발 프로세스",
        type: "다이어그램",
        thumbnail: "bg-gradient-to-br from-chart-5/30 to-primary/30"
      }
    ]
  },
  {
    id: "gamespot",
    name: "게임스팟",
    icon: "global",
    articles: [
      {
        id: 5,
        title: "클라우드 게이밍, 마침내 대중화되나",
        date: "2026.01.10",
        excerpt: "5G 네트워크의 확산과 함께 클라우드 게이밍 이용자가 전년 대비 150% 증가했다...",
        url: "#"
      },
      {
        id: 6,
        title: "차세대 콘솔 판매량 비교 분석",
        date: "2026.01.08",
        excerpt: "PlayStation 6와 Xbox Series Z의 출시 이후 판매량 데이터를 분석한 결과...",
        url: "#"
      }
    ],
    images: [
      {
        id: 4,
        title: "클라우드 게이밍 이용자 추이",
        type: "차트",
        thumbnail: "bg-gradient-to-br from-accent/30 to-chart-1/30"
      },
      {
        id: 5,
        title: "콘솔 판매량 비교",
        type: "비교표",
        thumbnail: "bg-gradient-to-br from-chart-2/30 to-chart-5/30"
      }
    ]
  },
  {
    id: "ign",
    name: "IGN Korea",
    icon: "media",
    articles: [
      {
        id: 7,
        title: "2026년 기대작 TOP 20",
        date: "2026.01.05",
        excerpt: "올해 출시 예정인 게임 중 가장 기대되는 작품 20개를 선정했다...",
        url: "#"
      }
    ],
    images: [
      {
        id: 6,
        title: "2026 기대작 포스터 콜라주",
        type: "이미지",
        thumbnail: "bg-gradient-to-br from-primary/30 to-accent/30"
      }
    ]
  }
]

const getSourceIcon = (icon: string) => {
  switch (icon) {
    case "game":
      return <div className="w-6 h-6 rounded bg-chart-1/20 flex items-center justify-center text-chart-1 text-xs font-bold">G</div>
    case "tech":
      return <div className="w-6 h-6 rounded bg-chart-2/20 flex items-center justify-center text-chart-2 text-xs font-bold">T</div>
    case "global":
      return <Globe className="w-5 h-5 text-chart-3" />
    case "media":
      return <Building2 className="w-5 h-5 text-chart-4" />
    default:
      return <FileText className="w-5 h-5 text-muted-foreground" />
  }
}

export function RelatedResources() {
  const [selectedSource, setSelectedSource] = useState<string>("all")

  const filteredSources = selectedSource === "all"
    ? sources
    : sources.filter(s => s.id === selectedSource)

  const allArticles = filteredSources.flatMap(s =>
    s.articles.map(a => ({ ...a, sourceName: s.name, sourceIcon: s.icon }))
  )
  const allImages = filteredSources.flatMap(s =>
    s.images.map(img => ({ ...img, sourceName: s.name, sourceIcon: s.icon }))
  )

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg">참고 자료</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Source Filter Tabs */}
        <div className="mb-4">
          <p className="text-xs text-muted-foreground mb-2">출처 선택</p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedSource("all")}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${selectedSource === "all"
                ? "bg-primary text-primary-foreground"
                : "bg-muted/50 text-muted-foreground hover:bg-muted"
                }`}
            >
              전체
            </button>
            {sources.map((source) => (
              <button
                key={source.id}
                onClick={() => setSelectedSource(source.id)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors flex items-center gap-1.5 ${selectedSource === source.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/50 text-muted-foreground hover:bg-muted"
                  }`}
              >
                {source.name}
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                  {source.articles.length + source.images.length}
                </Badge>
              </button>
            ))}
          </div>
        </div>

        <Tabs defaultValue="articles">
          <TabsList className="grid w-full grid-cols-2 mb-4">
            <TabsTrigger value="articles" className="gap-1 text-xs">
              <FileText className="w-3 h-3" />
              기사 ({allArticles.length})
            </TabsTrigger>
            <TabsTrigger value="images" className="gap-1 text-xs">
              <ImageIcon className="w-3 h-3" />
              이미지 ({allImages.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="articles">
            <ScrollArea className="h-[320px]">
              <div className="space-y-4">
                {selectedSource === "all" ? (
                  sources.map((source) => (
                    <div key={source.id} className="space-y-2">
                      <div className="flex items-center gap-2 sticky top-0 bg-card/90 backdrop-blur py-1">
                        {getSourceIcon(source.icon)}
                        <span className="text-sm font-medium text-foreground">{source.name}</span>
                        <Badge variant="outline" className="text-[10px]">
                          {source.articles.length}개 기사
                        </Badge>
                      </div>
                      <div className="space-y-2 pl-2 border-l-2 border-border/50 ml-3">
                        {source.articles.map((article) => (
                          <ArticleCard key={article.id} article={article} />
                        ))}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="space-y-3">
                    {allArticles.map((article) => (
                      <ArticleCard key={article.id} article={article} showSource />
                    ))}
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="images">
            <ScrollArea className="h-[320px]">
              <div className="space-y-4">
                {selectedSource === "all" ? (
                  sources.filter(s => s.images.length > 0).map((source) => (
                    <div key={source.id} className="space-y-2">
                      <div className="flex items-center gap-2 sticky top-0 bg-card/90 backdrop-blur py-1">
                        {getSourceIcon(source.icon)}
                        <span className="text-sm font-medium text-foreground">{source.name}</span>
                        <Badge variant="outline" className="text-[10px]">
                          {source.images.length}개 이미지
                        </Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-2 pl-2 border-l-2 border-border/50 ml-3">
                        {source.images.map((image) => (
                          <ImageCard key={image.id} image={image} />
                        ))}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="grid grid-cols-3 gap-3">
                    {allImages.map((image) => (
                      <ImageCard key={image.id} image={image} />
                    ))}
                  </div>
                )}
              </div>
            </ScrollArea>
            <p className="text-xs text-muted-foreground mt-3 text-center">
              클릭하여 스크립트에 삽입
            </p>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

function ArticleCard({
  article,
  showSource = false
}: {
  article: {
    id: number
    title: string
    date: string
    excerpt: string
    url: string
    sourceName?: string
    sourceIcon?: string
  }
  showSource?: boolean
}) {
  return (
    <a
      href={article.url}
      className="block p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors group"
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-medium text-sm text-foreground group-hover:text-primary transition-colors">
          {article.title}
        </h4>
        <ExternalLink className="w-4 h-4 text-muted-foreground flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
        {article.excerpt}
      </p>
      <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
        {showSource && article.sourceName && (
          <>
            <span>{article.sourceName}</span>
            <span className="w-1 h-1 rounded-full bg-muted-foreground" />
          </>
        )}
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {article.date}
        </div>
      </div>
    </a>
  )
}

function ImageCard({
  image
}: {
  image: {
    id: number
    title: string
    type: string
    thumbnail: string
  }
}) {
  return (
    <div className="aspect-square rounded-lg overflow-hidden cursor-pointer group relative">
      <div className={`w-full h-full ${image.thumbnail} flex items-center justify-center transition-transform group-hover:scale-105`}>
        <div className="text-center p-2">
          <ImageIcon className="w-6 h-6 mx-auto text-muted-foreground mb-1" />
          <p className="text-xs text-muted-foreground">{image.type}</p>
        </div>
      </div>
      <div className="absolute inset-0 bg-background/80 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
        <p className="text-xs text-foreground font-medium text-center px-2">{image.title}</p>
      </div>
    </div>
  )
}
