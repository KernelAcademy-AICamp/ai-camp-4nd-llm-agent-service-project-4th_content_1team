"use client"

import { useState, useEffect } from "react"
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

interface RelatedResourcesProps {
  apiReferences?: Array<{
    title: string;
    summary: string;
    source: string;
    date?: string;
    url: string;
    analysis?: {
      facts: string[];
      opinions: string[];
    };
    images?: Array<{
      url: string;
      caption?: string;
      is_chart?: boolean;
    }>;
  }>;
  activeCitationUrl?: string | null;
}

// URL 비교 헬퍼: 쿼리 파라미터 등 차이 무시, 도메인+경로 기준
function urlsMatch(url1?: string | null, url2?: string | null): boolean {
  if (!url1 || !url2) return false
  try {
    const u1 = new URL(url1)
    const u2 = new URL(url2)
    return u1.origin + u1.pathname === u2.origin + u2.pathname
  } catch {
    // URL 파싱 실패 시 문자열 포함 비교
    return url1.includes(url2) || url2.includes(url1)
  }
}

export function RelatedResources({ apiReferences, activeCitationUrl }: RelatedResourcesProps = {}) {
  const [selectedSource, setSelectedSource] = useState<string>("all")
  const [selectedArticle, setSelectedArticle] = useState<ArticleData | null>(null)
  const [displaySources, setDisplaySources] = useState<SourceData[]>([])

  // API 데이터가 있으면 변환해서 사용
  useEffect(() => {
    if (apiReferences && apiReferences.length > 0) {
      const grouped: Record<string, { articles: ArticleData[], images: ImageData[] }> = {};

      apiReferences.forEach((ref, idx) => {
        const sourceName = ref.source || "기타";
        if (!grouped[sourceName]) {
          grouped[sourceName] = { articles: [], images: [] };
        }

        // Article 추가
        grouped[sourceName].articles.push({
          id: idx,
          title: ref.title,
          date: ref.date || new Date().toISOString().split('T')[0],
          summary_short: ref.summary,
          url: ref.url,
          // 백엔드에서 온 analysis(facts, opinions)를 연동
          analysis: ref.analysis || { facts: [], opinions: [] }
        });

        // Images 추가
        if (ref.images && Array.isArray(ref.images)) {
          ref.images.forEach((img, imgIdx) => {
            grouped[sourceName].images.push({
              id: idx * 100 + imgIdx, // 고유 ID 생성
              title: img.caption || ref.title,
              type: img.is_chart ? "Chart" : "Scene",
              thumbnail: img.url, // 백엔드의 url을 UI의 thumbnail로 매핑
            });
          });
        }
      });

      const converted: SourceData[] = Object.keys(grouped).map(name => ({
        id: name.toLowerCase().replace(/\s+/g, '-'),
        name: name,
        icon: "media",
        articles: grouped[name].articles,
        images: grouped[name].images
      }));

      setDisplaySources(converted);
    }
  }, [apiReferences]);

  const filteredSources = selectedSource === "all"
    ? displaySources
    : displaySources.filter(s => s.id === selectedSource)

  const allArticles = filteredSources.flatMap(s =>
    s.articles.map(a => ({ ...a, sourceName: s.name, sourceIcon: s.icon }))
  )
  const allImages = filteredSources.flatMap(s =>
    s.images.map(img => ({ ...img, sourceName: s.name, sourceIcon: s.icon }))
  )

  return (
    <div className="relative h-full">
      <Card className="border-border/50 bg-card/50 backdrop-blur h-full flex flex-col">
        <CardHeader className="pb-4 flex-shrink-0">
          <CardTitle className="text-lg">참고 자료</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 flex flex-col">
          {displaySources.length === 0 ? (
            // Empty State
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-3 p-8">
                <div className="text-4xl">📰</div>
                <p className="text-muted-foreground text-sm">
                  "스크립트 생성 시<br />관련 뉴스가 표시됩니다"
                </p>
              </div>
            </div>
          ) : (
            <>
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
                  {displaySources.map((source) => (
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
                        {source.articles.length}
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
                        displaySources.map((source) => (
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
                                  isHighlighted={urlsMatch(activeCitationUrl, article.url)}
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
                              isHighlighted={urlsMatch(activeCitationUrl, article.url)}
                              onViewDetail={() => setSelectedArticle(article)}
                            />
                          ))}
                        </div>
                      )}
                      {allArticles.length === 0 && (
                        <div className="text-center text-muted-foreground text-sm py-10">
                          참고 자료가 없습니다.
                        </div>
                      )}
                    </div>
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="images" className="flex-1 min-h-0 relative">
                  <ScrollArea className="h-full pr-4">
                    <div className="space-y-4 pb-4">
                      {selectedSource === "all" ? (
                        displaySources.filter((s) => s.images.length > 0).map((source) => (
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
            </>
          )}
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
  isHighlighted = false,
  onViewDetail
}: {
  article: ArticleData
  showSource?: boolean
  isHighlighted?: boolean
  onViewDetail?: () => void
}) {
  return (
    <div
      className={`block p-3 rounded-lg transition-colors group relative ${isHighlighted
        ? "bg-primary/10 border-primary/50 border ring-1 ring-primary/30"
        : "bg-muted/30 hover:bg-muted/50 border border-transparent hover:border-border/50"
        }`}
    >
      <div className="flex items-start justify-between gap-2">
        <h4
          className="font-medium text-sm text-foreground group-hover:text-primary transition-colors line-clamp-1 cursor-pointer"
          onClick={() => article.url && window.open(article.url, "_blank", "noopener,noreferrer")}
          title={article.url || "URL 없음"}
        >
          {article.title}
        </h4>
        {article.url && (
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 text-muted-foreground hover:text-primary transition-colors"
            onClick={(e) => e.stopPropagation()}
            title="원본 기사 열기"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
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
  const hasValidImage = image.thumbnail && (
    image.thumbnail.startsWith('data:image') ||
    image.thumbnail.startsWith('http')
  )

  return (
    <div className="aspect-square rounded-lg overflow-hidden cursor-pointer group relative bg-muted/30">
      {hasValidImage ? (
        <img
          src={image.thumbnail}
          alt={image.title}
          className="w-full h-full object-cover transition-transform group-hover:scale-105"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center">
          <div className="text-center p-2">
            <ImageIcon className="w-6 h-6 mx-auto text-muted-foreground mb-1" />
            <p className="text-xs text-muted-foreground">{image.type}</p>
          </div>
        </div>
      )}
      <div className="absolute inset-0 bg-background/80 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
        <p className="text-xs text-foreground font-medium text-center px-2">{image.title}</p>
      </div>
    </div>
  )
}
