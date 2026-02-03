"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../components/ui/tabs"
import { Badge } from "../../../components/ui/badge"
import { Button } from "../../../components/ui/button"
import { ExternalLink, Target, MessageSquare, FileText, ImageIcon, Clock, Eye, Copy, X, Check, Globe, Building2 } from "lucide-react"
import { ScrollArea } from "../../../components/ui/scroll-area"

// --- Data Types ---

interface AnalysisData {
  facts: string[]
  opinions: string[]
}

interface ArticleData {
  id: number
  title: string
  date: string
  summary_short: string
  url: string
  analysis?: AnalysisData
  sourceName?: string
  sourceIcon?: string
}

interface ImageData {
  id: number
  title: string
  type: string
  thumbnail: string
  sourceName?: string
  sourceIcon?: string
}

interface SourceData {
  id: string
  name: string
  icon: string
  articles: ArticleData[]
  images: ImageData[]
}

// --- Mock Data (Updated Structure) ---

const sources: SourceData[] = [
  {
    id: "kotra",
    name: "KOTRA",
    icon: "global",
    articles: [
      {
        id: 1,
        title: "2026년 불가리아에서 달라지는 것들",
        date: "2026.02.02",
        summary_short: "2026년 불가리아는 유로화를 공식 도입하고 최저임금을 인상하여 경제 시스템의 격변을 예고하고 있다.",
        url: "#",
        analysis: {
          facts: [
            "2026년 1월 1일부터 불가리아는 유로화를 법정화폐로 도입하였다.",
            "불가리아의 2026년 실질 GDP 성장률 전망치는 IMF에 따르면 3.1%, OECD에 따르면 2.6%이다.",
            "2026년 불가리아의 최저임금은 1,213 BGN으로, 이는 전년 대비 약 12.6% 인상된 수치이다.",
            "불가리아의 실업률은 역대 최저 수준인 3.5%이다."
          ],
          opinions: [
            "[전문가] IMF는 유로화 도입이 경제 전반에 긍정적 모멘텀을 제공할 것이라고 분석했다.",
            "[업계] 불가리아의 유럽화는 인프라 및 인적 자본에 대한 투자를 확대할 것으로 예상된다.",
            "[분석] OECD는 고물가 지속이 소비 위축을 초래할 것이라고 경고했다.",
            "[전문가] 유로화 도입에 따른 신용등급 상향 조정이 외국인 투자 유치 증가로 이어질 것이라고 전망된다."
          ]
        }
      }
    ],
    images: [] // 이미지 없음
  },
  {
    id: "newspim",
    name: "뉴스핌",
    icon: "media",
    articles: [
      {
        id: 2,
        title: "마스턴투자운용, '한국 부동산 시장 2026년 전망' 사내 세미나 개최",
        date: "2026.01.27",
        summary_short: "마스턴투자운용이 2026년 한국 부동산 시장 전망을 발표했다.",
        url: "#",
        analysis: {
          facts: [
            "2026년 상업용 부동산 시장의 연간 거래규모는 최대 31.9조원으로 예상된다.",
            "2026년 오피스 거래 규모는 최대 20.2조원으로 예상된다.",
            "한국의 최근 5년간 연 환산 부동산 투자수익률은 8.5%로 가장 높은 성과를 기록했다."
          ],
          opinions: [
            "[전문가] 불확실성은 준비되지 않은 투자자에게는 리스크이지만, 구조적 흐름을 읽는 투자자에게는 할인된 기회가 될 수 있다.",
            "[해석] 2026년은 전통적인 입지 분석을 넘어 기술적 수용성과 운용 역량이 수익률을 결정짓는 시대가 본격적으로 시작되는 시점이다.",
            "[전망] 2029년을 기점으로 대규모 신규 공급이 집중되면서 임차인 우위 시장으로 전환될 가능성이 있다.",
            "[업계] 물류센터 임대시장의 펀더멘털 약화에도 불구하고 해외 투자자들을 중심으로 저평가 자산 매입 수요가 유입되고 있다."
          ]
        }
      }
    ],
    images: []
  },
  {
    id: "bizhankook",
    name: "비즈한국",
    icon: "media",
    articles: [
      {
        id: 3,
        title: "[부동산 인사이트] 강남·마용성 숨고를 때, 강서가 치고 올라온 이유",
        date: "2026.02.02",
        summary_short: "서울 강서구가 부동산 시장에서 주간 상승률 1위를 기록하며 주목받고 있다.",
        url: "#",
        analysis: {
          facts: [
            "2026년 2월, 서울 강서구가 주간 상승률 1위를 기록했다.",
            "강서구의 주력 단지들은 9억 원에서 14억 원 사이에 포진해 있다.",
            "서울의 신규 입주 물량은 향후 2~3년간 급감할 예정이다."
          ],
          opinions: [
            "[전망] 강서구는 실수요자들의 피난처이자 정착지가 될 것이다.",
            "[해석] 마곡은 이제 단순한 주거지가 아니다. 서울 서부권의 경제 심장이다.",
            "[분석] 강서구의 상승세는 마포구와 성동구의 시세를 일정 수준 따라잡을 것으로 전망된다.",
            "[전문가] 지금 시점에서의 추격매수는 냉철한 선별이 필요하다."
          ]
        }
      }
    ],
    images: []
  }
]

// --- Helper Components ---

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

// --- Main Component ---

export function RelatedResources() {
  const [selectedSource, setSelectedSource] = useState<string>("all")
  const [selectedArticle, setSelectedArticle] = useState<ArticleData | null>(null) // Detail View State

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
    <div className="relative h-full"> {/* Container for relative positioning of overlay */}
      <Card className="border-border/50 bg-card/50 backdrop-blur h-full flex flex-col">
        <CardHeader className="pb-4 flex-shrink-0">
          <CardTitle className="text-lg">참고 자료</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 flex flex-col">
          {/* Source Filter Tabs */}
          <div className="mb-4 flex-shrink-0">
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

          <Tabs defaultValue="articles" className="flex-1 flex flex-col min-h-0">
            <TabsList className="grid w-full grid-cols-2 mb-4 flex-shrink-0">
              <TabsTrigger value="articles" className="gap-1 text-xs">
                <FileText className="w-3 h-3" />
                기사 ({allArticles.length})
              </TabsTrigger>
              <TabsTrigger value="images" className="gap-1 text-xs">
                <ImageIcon className="w-3 h-3" />
                이미지 ({allImages.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="articles" className="flex-1 min-h-0 relative">
              <ScrollArea className="h-full pr-4">
                <div className="space-y-4 pb-4">
                  {selectedSource === "all" ? (
                    sources.map((source) => (
                      <div key={source.id} className="space-y-2">
                        <div className="flex items-center gap-2 sticky top-0 bg-card/90 backdrop-blur py-1 z-10">
                          {getSourceIcon(source.icon)}
                          <span className="text-sm font-medium text-foreground">{source.name}</span>
                          <Badge variant="outline" className="text-[10px]">
                            {source.articles.length}개 기사
                          </Badge>
                        </div>
                        <div className="space-y-2 pl-2 border-l-2 border-border/50 ml-3">
                          {source.articles.map((article) => (
                            <ArticleCard
                              key={article.id}
                              article={article}
                              onViewDetail={() => setSelectedArticle(article)}
                            />
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="space-y-3">
                      {allArticles.map((article) => (
                        <ArticleCard
                          key={article.id}
                          article={article}
                          showSource
                          onViewDetail={() => setSelectedArticle(article)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="images" className="flex-1 min-h-0 relative">
              <ScrollArea className="h-full pr-4">
                <div className="space-y-4 pb-4">
                  {selectedSource === "all" ? (
                    sources.filter(s => s.images.length > 0).map((source) => (
                      <div key={source.id} className="space-y-2">
                        <div className="flex items-center gap-2 sticky top-0 bg-card/90 backdrop-blur py-1 z-10">
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
              <p className="text-xs text-muted-foreground mt-3 text-center mb-2">
                클릭하여 스크립트에 삽입
              </p>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* --- Detail View Overlay (Modal) --- */}
      {selectedArticle && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <Card className="w-full max-w-lg h-full max-h-[600px] flex flex-col shadow-2xl border-primary/20 bg-card">
            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2 border-b">
              <div className="space-y-1 pr-4">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <Badge variant="outline" className="text-[10px]">{selectedArticle.sourceName || "News"}</Badge>
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {selectedArticle.date}</span>
                </div>
                <CardTitle className="text-base font-bold leading-tight">
                  <a href={selectedArticle.url} target="_blank" rel="noreferrer" className="hover:underline hover:text-primary transition-colors flex items-center gap-1">
                    {selectedArticle.title}
                    <ExternalLink className="w-3 h-3 opacity-50" />
                  </a>
                </CardTitle>
              </div>
              <Button size="icon" variant="ghost" className="h-6 w-6 -mr-2" onClick={() => setSelectedArticle(null)}>
                <X className="w-4 h-4" />
              </Button>
            </CardHeader>
            <CardContent className="flex-1 overflow-hidden p-0">
              <ScrollArea className="h-full p-4">
                {/* Summary Short */}
                <div className="mb-6 bg-muted/30 p-3 rounded-md border border-border/50">
                  <h4 className="text-xs font-semibold text-muted-foreground mb-1">핵심 요약</h4>
                  <p className="text-sm font-medium leading-relaxed">{selectedArticle.summary_short}</p>
                </div>

                {/* 2-Column Analysis */}
                <div className="grid grid-cols-1 gap-4">
                  {/* Facts Column */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-blue-500 font-semibold text-sm border-b pb-1 border-blue-500/20">
                      <Target className="w-4 h-4" />
                      <span>팩트 (Facts)</span>
                    </div>
                    <div className="bg-blue-500/5 rounded-md p-3 space-y-2">
                      {selectedArticle.analysis?.facts && selectedArticle.analysis.facts.length > 0 ? (
                        selectedArticle.analysis.facts.map((fact, idx) => (
                          <div key={idx} className="flex items-start gap-2 text-sm text-foreground/90">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 flex-shrink-0" />
                            <span className="leading-snug">{fact}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-muted-foreground">추출된 팩트가 없습니다.</p>
                      )}
                    </div>
                  </div>

                  {/* Opinions Column */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-amber-500 font-semibold text-sm border-b pb-1 border-amber-500/20">
                      <MessageSquare className="w-4 h-4" />
                      <span>전망 및 해석 (Insights)</span>
                    </div>
                    <div className="bg-amber-500/5 rounded-md p-3 space-y-2">
                      {selectedArticle.analysis?.opinions && selectedArticle.analysis.opinions.length > 0 ? (
                        selectedArticle.analysis.opinions.slice(0, 5).map((op, idx) => (
                          <div key={idx} className="flex items-start gap-2 text-sm text-foreground/90">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 flex-shrink-0" />
                            <span className="leading-snug">
                              {/* 태그 강조 (간단한 파싱) */}
                              {op.startsWith('[') && op.includes(']') ? (
                                <>
                                  <span className="font-bold text-amber-600 mr-1">{op.split(']')[0] + ']'}</span>
                                  {op.split(']').slice(1).join(']')}
                                </>
                              ) : (
                                op
                              )}
                            </span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-muted-foreground">관련 전문가 의견이나 분석이 없습니다.</p>
                      )}
                    </div>
                  </div>
                </div>
              </ScrollArea>
            </CardContent>

            {/* Footer Actions */}
            <div className="p-3 border-t bg-muted/20 flex gap-2 justify-end">
              <Button variant="outline" size="sm" className="h-8 text-xs gap-1">
                <Copy className="w-3 h-3" />
                팩트 복사
              </Button>
              <Button variant="default" size="sm" className="h-8 text-xs gap-1 bg-blue-600 hover:bg-blue-700">
                <Check className="w-3 h-3" />
                대본 반영
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

function ArticleCard({
  article,
  showSource = false,
  onViewDetail
}: {
  article: ArticleData
  showSource?: boolean
  onViewDetail?: () => void
}) {
  return (
    <div
      className="block p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors group relative border border-transparent hover:border-border/50"
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-medium text-sm text-foreground group-hover:text-primary transition-colors line-clamp-1">
          {article.title}
        </h4>
      </div>

      {/* Short Summary instead of excerpt */}
      <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2 leading-relaxed">
        {article.summary_short}
      </p>

      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {showSource && article.sourceName && (
            <>
              <span className="font-medium text-foreground/80">{article.sourceName}</span>
              <span className="w-1 h-1 rounded-full bg-muted-foreground/50" />
            </>
          )}
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {article.date}
          </div>
        </div>

        {/* View Details Button */}
        <Button
          variant="secondary"
          size="sm"
          className="h-6 text-[10px] px-2 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => {
            e.stopPropagation()
            onViewDetail?.()
          }}
        >
          <Eye className="w-3 h-3 mr-1" />
          상세보기
        </Button>
      </div>
    </div>
  )
}

function ImageCard({
  image
}: {
  image: ImageData
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
