"use client"

import { useState, useEffect } from "react"
import { DashboardSidebar } from "../dashboard/components/sidebar"
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs"
import { Input } from "../../components/ui/input"
import { Button } from "../../components/ui/button"
import { Badge } from "../../components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "../../components/ui/avatar"
import { ScrollArea } from "../../components/ui/scroll-area"
import { BarChart3, Users, Search, FileText, Loader2, Plus, Sparkles, CheckCircle2, AlertTriangle, Lightbulb, MessageSquare } from "lucide-react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  searchChannels,
  addCompetitorChannel,
  getCompetitorChannels,
  analyzeRecentVideo,
  refreshCompetitorVideos,
  type ChannelSearchResult,
  type CompetitorChannelResponse,
  type CompetitorChannelListResponse,
  type CompetitorChannelVideo,
  type RecentVideoAnalyzeResponse,
} from "../../lib/api/index"

function VideoAnalysisResults({ video }: { video: CompetitorChannelVideo }) {
  return (
    <div className="mt-3 space-y-3 border-t border-border/50 pt-3">
      {/* 성공이유 */}
      {video.analysis_strengths && video.analysis_strengths.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
            <span className="text-xs font-semibold text-green-600">성공이유</span>
          </div>
          <ul className="space-y-1 pl-5">
            {video.analysis_strengths.map((item, idx) => (
              <li key={idx} className="text-xs text-muted-foreground list-disc">{item}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 부족한점 */}
      {video.analysis_weaknesses && video.analysis_weaknesses.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-orange-500" />
            <span className="text-xs font-semibold text-orange-600">부족한점</span>
          </div>
          <ul className="space-y-1 pl-5">
            {video.analysis_weaknesses.map((item, idx) => (
              <li key={idx} className="text-xs text-muted-foreground list-disc">{item}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 유저 반응 */}
      {video.comment_insights && (
        (video.comment_insights.reactions?.length > 0 || video.comment_insights.needs?.length > 0) && (
          <div className="space-y-2">
            <div className="flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-purple-500" />
              <span className="text-xs font-semibold text-purple-600">유저 반응</span>
            </div>
            {video.comment_insights.reactions?.length > 0 && (
              <div className="space-y-1 pl-5">
                <span className="text-xs font-medium text-muted-foreground">주요 반응</span>
                <ul className="space-y-1">
                  {video.comment_insights.reactions.map((item, idx) => (
                    <li key={idx} className="text-xs text-muted-foreground list-disc ml-4">{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {video.comment_insights.needs?.length > 0 && (
              <div className="space-y-1 pl-5">
                <span className="text-xs font-medium text-muted-foreground">시청자가 원하는 콘텐츠</span>
                <ul className="space-y-1">
                  {video.comment_insights.needs.map((item, idx) => (
                    <li key={idx} className="text-xs text-muted-foreground list-disc ml-4">{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )
      )}

      {/* 내 채널에 적용할 포인트 */}
      {video.applicable_points && video.applicable_points.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <Lightbulb className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-xs font-semibold text-blue-600">내 채널에 적용할 포인트</span>
          </div>
          <ul className="space-y-1 pl-5">
            {video.applicable_points.map((item, idx) => (
              <li key={idx} className="text-xs text-muted-foreground list-disc">{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function AnalysisPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [shouldSearch, setShouldSearch] = useState(false)
  const [analyzingVideoId, setAnalyzingVideoId] = useState<string | null>(null)
  const [expandedVideoId, setExpandedVideoId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // 채널 검색 쿼리
  const { data: searchResults, isLoading, isError, error } = useQuery({
    queryKey: ['channel-search', searchQuery],
    queryFn: () => searchChannels(searchQuery),
    enabled: shouldSearch && !!searchQuery.trim(),
    staleTime: 1000 * 60 * 5,
  })

  // 등록된 경쟁 채널 목록
  const { data: competitorList, isLoading: isLoadingList, error: listError } = useQuery({
    queryKey: ['competitor-channels'],
    queryFn: async () => {
      console.log('경쟁 채널 목록 조회 중...')
      const result = await getCompetitorChannels()
      console.log('조회 결과:', result)
      return result
    },
    staleTime: 1000 * 60 * 5,
  })

  // 페이지 진입 시 최신 영상 자동 갱신 (분석 중이 아닐 때만 invalidate)
  const refreshMutation = useMutation({
    mutationFn: refreshCompetitorVideos,
    onSuccess: (data) => {
      if (data.updated_channels > 0 && !analyzingVideoId) {
        console.log(`${data.updated_channels}개 채널 영상 갱신됨`)
        queryClient.invalidateQueries({ queryKey: ['competitor-channels'] })
      }
    },
    onError: (error) => {
      console.warn('영상 갱신 실패 (기존 데이터 유지):', error)
    },
  })

  useEffect(() => {
    refreshMutation.mutate()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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

  // AI 영상 분석 mutation (캐시 직접 업데이트로 스크롤 유지)
  const analysisMutation = useMutation({
    mutationFn: (videoId: string) => analyzeRecentVideo(videoId),
    onMutate: (videoId) => {
      setAnalyzingVideoId(videoId)
    },
    onSuccess: (data: RecentVideoAnalyzeResponse) => {
      console.log('AI 분석 결과:', data)
      setExpandedVideoId(data.video_id)

      // invalidateQueries 대신 캐시 직접 업데이트 → 스크롤 위치 유지
      queryClient.setQueryData(
        ['competitor-channels'],
        (old: CompetitorChannelListResponse | undefined) => {
          if (!old) return old
          return {
            ...old,
            channels: old.channels.map((ch) => ({
              ...ch,
              recent_videos: ch.recent_videos?.map((v) =>
                v.video_id === data.video_id
                  ? {
                      ...v,
                      analysis_strengths: data.analysis_strengths,
                      analysis_weaknesses: data.analysis_weaknesses,
                      applicable_points: data.applicable_points,
                      comment_insights: data.comment_insights,
                      analyzed_at: data.analyzed_at,
                    }
                  : v
              ),
            })),
          }
        }
      )
    },
    onError: (error: any) => {
      console.error('AI 분석 실패:', error)
      alert('AI 분석 실패: ' + (error?.response?.data?.detail || '알 수 없는 오류'))
    },
    onSettled: () => {
      setAnalyzingVideoId(null)
    },
  })

  const handleAnalyzeVideo = (video: CompetitorChannelVideo, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()

    // 이미 분석 완료된 영상이면 결과 토글
    if (video.analyzed_at) {
      setExpandedVideoId(expandedVideoId === video.video_id ? null : video.video_id)
      return
    }

    // 분석 실행
    analysisMutation.mutate(video.video_id)
  }

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

  const getAnalysisButton = (video: CompetitorChannelVideo) => {
    const isAnalyzing = analyzingVideoId === video.video_id
    const isAnalyzed = !!video.analyzed_at
    const isExpanded = expandedVideoId === video.video_id

    if (isAnalyzing) {
      return (
        <Button size="sm" variant="outline" className="w-full mt-2 gap-1 text-xs" disabled>
          <Loader2 className="w-3 h-3 animate-spin" />
          AI 분석 중...
        </Button>
      )
    }

    if (isAnalyzed) {
      return (
        <Button
          size="sm"
          variant={isExpanded ? "default" : "outline"}
          className="w-full mt-2 gap-1 text-xs"
          onClick={(e) => handleAnalyzeVideo(video, e)}
        >
          <CheckCircle2 className="w-3 h-3" />
          {isExpanded ? "분석 결과 닫기" : "AI 분석 결과 보기"}
        </Button>
      )
    }

    return (
      <Button
        size="sm"
        variant="outline"
        className="w-full mt-2 gap-1 text-xs"
        onClick={(e) => handleAnalyzeVideo(video, e)}
      >
        <Sparkles className="w-3 h-3" />
        AI 영상 분석
      </Button>
    )
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
                  {isLoadingList ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    </div>
                  ) : listError ? (
                    <div className="text-sm text-destructive py-4">
                      조회 실패: {(listError as any)?.response?.data?.detail || '알 수 없는 오류'}
                    </div>
                  ) : !competitorList || competitorList.total === 0 ? (
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
                    <ScrollArea className="h-[600px]">
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

                            {/* 최신 영상 3개 */}
                            <div className="space-y-2">
                              <h4 className="text-sm font-semibold text-muted-foreground">최신 영상</h4>
                              {channel.recent_videos && channel.recent_videos.length > 0 ? (
                                <div className="grid grid-cols-3 gap-3">
                                  {channel.recent_videos.map((video) => (
                                    <div
                                      key={video.id}
                                      className="border border-border/50 rounded-lg overflow-hidden bg-card hover:border-primary/50 transition-colors"
                                    >
                                      <a
                                        href={`https://www.youtube.com/watch?v=${video.video_id}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                      >
                                        <img
                                          src={video.thumbnail_url}
                                          alt={video.title}
                                          className="w-full aspect-video object-cover"
                                        />
                                      </a>
                                      <div className="p-2">
                                        <a
                                          href={`https://www.youtube.com/watch?v=${video.video_id}`}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                        >
                                          <p className="text-xs font-medium line-clamp-2 mb-2 hover:text-primary">
                                            {video.title}
                                          </p>
                                        </a>
                                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                          <span>조회수 {formatNumber(video.view_count)}</span>
                                          <span>•</span>
                                          <span>좋아요 {formatNumber(video.like_count)}</span>
                                        </div>
                                        <div className="text-xs text-muted-foreground mt-1">
                                          댓글 {formatNumber(video.comment_count)}
                                        </div>
                                        {getAnalysisButton(video)}
                                        {expandedVideoId === video.video_id && video.analyzed_at && (
                                          <VideoAnalysisResults video={video} />
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-xs text-muted-foreground py-4 text-center">
                                  최신 영상 정보가 없습니다
                                </p>
                              )}
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
