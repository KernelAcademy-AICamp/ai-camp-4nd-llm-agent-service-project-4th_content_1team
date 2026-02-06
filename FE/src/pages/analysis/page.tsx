"use client"

import { useState } from "react"
import { DashboardSidebar } from "../dashboard/components/sidebar"
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs"
import { Input } from "../../components/ui/input"
import { Button } from "../../components/ui/button"
import { Badge } from "../../components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "../../components/ui/avatar"
import { ScrollArea } from "../../components/ui/scroll-area"
import { BarChart3, Users, Search, FileText, Loader2, Plus } from "lucide-react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  searchChannels,
  addCompetitorChannel,
  getCompetitorChannels,
  type ChannelSearchResult,
  type CompetitorChannelResponse,
} from "../../lib/api/index"

export default function AnalysisPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [shouldSearch, setShouldSearch] = useState(false)
  const queryClient = useQueryClient()

  // 채널 검색 쿼리
  const { data: searchResults, isLoading, isError, error } = useQuery({
    queryKey: ['channel-search', searchQuery],
    queryFn: () => searchChannels(searchQuery),
    enabled: shouldSearch && !!searchQuery.trim(),
    staleTime: 1000 * 60 * 5,
  })

  // 등록된 경쟁 채널 목록
  const { data: competitorList } = useQuery({
    queryKey: ['competitor-channels'],
    queryFn: getCompetitorChannels,
    staleTime: 1000 * 60 * 5,
  })

  // 경쟁 채널 추가 mutation
  const addMutation = useMutation({
    mutationFn: (channel: ChannelSearchResult) => 
      addCompetitorChannel({
        channel_id: channel.channel_id,
        title: channel.title,
        description: channel.description,
        custom_url: channel.custom_url,
        thumbnail_url: channel.thumbnail_url,
        subscriber_count: channel.subscriber_count,
        view_count: channel.view_count,
        video_count: channel.video_count,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitor-channels'] })
      // 검색 결과 초기화
      setSearchQuery("")
      setShouldSearch(false)
    },
  })

  const handleSearch = () => {
    if (searchQuery.trim()) {
      setShouldSearch(true)
    }
  }

  const handleAddCompetitor = (channel: ChannelSearchResult) => {
    addMutation.mutate(channel)
  }

  // 검색 초기화
  const handleQueryChange = (value: string) => {
    setSearchQuery(value)
    if (!value.trim()) {
      setShouldSearch(false)
    }
  }

  function formatNumber(num: number): string {
    if (num >= 10000) {
      return `${(num / 10000).toFixed(1)}만`
    }
    return num.toLocaleString()
  }

  return (
    <div className="min-h-screen bg-background flex">
      <DashboardSidebar />

      <main className="flex-1 p-6 overflow-auto">
        <div className="max-w-[1400px] mx-auto space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">채널 분석</h1>
            <p className="text-muted-foreground">
              내 채널과 경쟁 유튜버를 분석하고 최적의 콘텐츠 전략을 세우세요
            </p>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="competitor" className="w-full">
            <TabsList className="grid w-full grid-cols-4 mb-6">
              <TabsTrigger value="my-channel" className="gap-2">
                <BarChart3 className="w-4 h-4" />
                내 유튜브 분석
              </TabsTrigger>
              <TabsTrigger value="competitor" className="gap-2">
                <Users className="w-4 h-4" />
                경쟁 유튜버 분석
              </TabsTrigger>
              <TabsTrigger value="topics" className="gap-2">
                <FileText className="w-4 h-4" />
                주제 추천
              </TabsTrigger>
              <TabsTrigger value="trends" className="gap-2">
                <BarChart3 className="w-4 h-4" />
                실시간 트렌드
              </TabsTrigger>
            </TabsList>

            {/* 내 유튜브 분석 */}
            <TabsContent value="my-channel" className="space-y-6">
              <Card className="border-border/50 bg-card/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-lg">내 채널 통계</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    구현 예정: 구독자 추이, 조회수 분석, 인기 영상 등
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            {/* 경쟁 유튜버 분석 */}
            <TabsContent value="competitor" className="space-y-6">
              <Card className="border-border/50 bg-card/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-lg">경쟁 유튜버 추가</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                          placeholder="유튜버 이름 또는 채널 URL을 입력하세요"
                          value={searchQuery}
                          onChange={(e) => handleQueryChange(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleSearch()
                            }
                          }}
                          className="pl-10"
                        />
                      </div>
                      <Button 
                        onClick={handleSearch}
                        disabled={!searchQuery.trim() || isLoading}
                        className="gap-2"
                      >
                        {isLoading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Search className="w-4 h-4" />
                        )}
                        검색
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      채널 이름, URL, 또는 @핸들을 입력하여 경쟁 유튜버를 추가하세요
                    </p>

                    {/* 검색 결과 */}
                    {shouldSearch && (
                      <div className="mt-4">
                        {isLoading && (
                          <div className="flex items-center justify-center py-8">
                            <Loader2 className="w-6 h-6 animate-spin text-primary" />
                          </div>
                        )}

                        {isError && (
                          <div className="text-sm text-destructive py-4">
                            검색 실패: {(error as any)?.response?.data?.detail || '알 수 없는 오류'}
                          </div>
                        )}

                        {searchResults && searchResults.total_results > 0 && (
                          <div className="space-y-2">
                            <p className="text-xs text-muted-foreground mb-2">
                              검색 결과 {searchResults.total_results}개
                            </p>
                            <ScrollArea className="max-h-[400px]">
                              <div className="space-y-2 pr-4">
                                {searchResults.channels.map((channel) => (
                                  <div
                                    key={channel.channel_id}
                                    className="flex items-center gap-4 p-3 rounded-lg border border-border/50 hover:border-border hover:bg-muted/30 transition-colors"
                                  >
                                    <Avatar className="w-12 h-12">
                                      <AvatarImage src={channel.thumbnail_url} alt={channel.title} />
                                      <AvatarFallback>{channel.title.slice(0, 2)}</AvatarFallback>
                                    </Avatar>
                                    <div className="flex-1 min-w-0">
                                      <h4 className="font-medium text-sm text-foreground truncate">
                                        {channel.title}
                                      </h4>
                                      <div className="flex items-center gap-2 mt-1">
                                        <Badge variant="secondary" className="text-xs">
                                          구독자 {formatNumber(channel.subscriber_count)}
                                        </Badge>
                                        <span className="text-xs text-muted-foreground">
                                          영상 {channel.video_count}개
                                        </span>
                                      </div>
                                    </div>
                                    <Button
                                      size="sm"
                                      onClick={() => handleAddCompetitor(channel)}
                                      className="gap-1"
                                    >
                                      <Plus className="w-4 h-4" />
                                      추가하기
                                    </Button>
                                  </div>
                                ))}
                              </div>
                            </ScrollArea>
                          </div>
                        )}

                        {searchResults && searchResults.total_results === 0 && (
                          <div className="text-sm text-muted-foreground py-4 text-center">
                            검색 결과가 없습니다
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* 등록된 경쟁 유튜버 목록 */}
              <Card className="border-border/50 bg-card/50 backdrop-blur">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">등록된 경쟁 유튜버</CardTitle>
                    {competitorList && competitorList.total > 0 && (
                      <Badge variant="secondary">{competitorList.total}</Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {!competitorList || competitorList.total === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <Users className="w-12 h-12 text-muted-foreground mb-4" />
                      <h3 className="font-medium text-foreground mb-2">
                        아직 등록된 경쟁 유튜버가 없습니다
                      </h3>
                      <p className="text-sm text-muted-foreground max-w-[300px]">
                        위 검색창을 통해 경쟁 유튜버를 추가하고 채널을 비교 분석하세요
                      </p>
                    </div>
                  ) : (
                    <ScrollArea className="max-h-[600px]">
                      <div className="space-y-4 pr-4">
                        {competitorList.channels.map((channel: CompetitorChannelResponse) => (
                          <div
                            key={channel.id}
                            className="border border-border/50 rounded-lg p-4 space-y-4 bg-muted/20"
                          >
                            {/* 채널 기본 정보 */}
                            <div className="flex items-center gap-4">
                              <Avatar className="w-16 h-16">
                                <AvatarImage src={channel.thumbnail_url} alt={channel.title} />
                                <AvatarFallback>{channel.title.slice(0, 2)}</AvatarFallback>
                              </Avatar>
                              <div className="flex-1">
                                <h3 className="font-semibold text-foreground">{channel.title}</h3>
                                {channel.custom_url && (
                                  <p className="text-sm text-muted-foreground">@{channel.custom_url}</p>
                                )}
                                <p className="text-sm text-muted-foreground mt-1">
                                  구독자 {formatNumber(channel.subscriber_count)}
                                </p>
                              </div>
                            </div>

                            {/* 분석 카드 3개 */}
                            <div className="grid grid-cols-3 gap-3">
                              {/* 강점 */}
                              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
                                <h4 className="text-xs font-semibold text-emerald-500 mb-2">강점</h4>
                                {channel.strengths && channel.strengths.length > 0 ? (
                                  <ul className="text-xs text-muted-foreground space-y-1">
                                    {channel.strengths.slice(0, 3).map((str, i) => (
                                      <li key={i} className="line-clamp-2">• {str}</li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="text-xs text-muted-foreground">
                                    실시간 스트리밍 병행으로 시청자 충성도 높음<br/>
                                    밈/유머 활용에 능숙<br/>
                                    업로드 주기가 매우 일정함 (주 3회)
                                  </p>
                                )}
                              </div>

                              {/* 채널 성격 */}
                              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                                <h4 className="text-xs font-semibold text-blue-500 mb-2">채널 성격</h4>
                                <p className="text-xs text-muted-foreground">
                                  {channel.channel_personality || 
                                    "유머와 리액션 중심의 엔터테인먼트형 게임 채널. 과장된 리액션과 편집으로 재미 중시."}
                                </p>
                              </div>

                              {/* 시청자 타겟 */}
                              <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
                                <h4 className="text-xs font-semibold text-amber-500 mb-2">시청자 타겟</h4>
                                <p className="text-xs text-muted-foreground">
                                  {channel.target_audience || 
                                    "15~24세 남성이 주력, 캐주얼 게이머 및 스트리밍 시청을 즐기는 Z세대가 핵심 시청자."}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* 주제 추천 */}
            <TabsContent value="topics" className="space-y-6">
              <Card className="border-border/50 bg-card/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-lg">AI 주제 추천</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    구현 예정: 트렌드 기반 주제 추천
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            {/* 실시간 트렌드 */}
            <TabsContent value="trends" className="space-y-6">
              <Card className="border-border/50 bg-card/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-lg">실시간 트렌드</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    구현 예정: 실시간 검색 트렌드, 급상승 키워드
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  )
}
