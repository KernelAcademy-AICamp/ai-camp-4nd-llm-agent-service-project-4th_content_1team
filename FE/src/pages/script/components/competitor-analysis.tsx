"use client"

import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Badge } from "../../../components/ui/badge"
import { Button } from "../../../components/ui/button"
import { ScrollArea } from "../../../components/ui/scroll-area"
import {
  Play,
  Eye,
  ThumbsUp,
  MessageSquare,
  ExternalLink,
  TrendingUp,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  RefreshCw
} from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { searchYouTubeVideos, saveCompetitorVideos, analyzeVideoContent, type VideoItem } from "../../../lib/api/index"

// TODO: 지워야함 샘플 데이터 (하드코딩)
const SAMPLE_KEYWORDS = [
  "AI 웹서비스 만들기",
  "ChatGPT 웹앱 만들기",
  "바이브 코딩"

]

// YouTube API 응답을 UI 형식으로 변환
function formatNumber(num: number): string {
  if (num >= 10000) {
    return `${(num / 10000).toFixed(1)}만`
  }
  return num.toLocaleString()
}

export function CompetitorAnalysis() {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // YouTube 검색 API 호출
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['youtube-search', SAMPLE_KEYWORDS.join(' ')],
    queryFn: async () => {
      return await searchYouTubeVideos({
        keywords: SAMPLE_KEYWORDS.join(' '),
        max_results: 10
      })
    },
    staleTime: 1000 * 60 * 10, // 10분간 캐시
  })

  // 검색 결과 10개를 DB에 자동 저장
  const savedRef = useRef<string | null>(null)
  useEffect(() => {
    if (!data?.videos.length) return
    const key = data.videos.map(v => v.video_id).join(',')
    if (savedRef.current === key) return
    savedRef.current = key

    saveCompetitorVideos({
      policy_json: { query: data.query, keywords: SAMPLE_KEYWORDS },
      videos: data.videos.map((v: VideoItem) => ({
        youtube_video_id: v.video_id,
        url: `https://www.youtube.com/watch?v=${v.video_id}`,
        title: v.title,
        channel_title: v.channel_title,
        published_at: v.published_at,
        metrics_json: {
          view_count: v.statistics.view_count,
          like_count: v.statistics.like_count,
          comment_count: v.statistics.comment_count,
          popularity_score: v.popularity_score,
          days_since_upload: v.days_since_upload,
        },
        caption_meta_json: {
          has_caption: v.has_caption,
        },
      })),
    })
      .then(() => {
        // TODO: 나중에 테스트하기 위해 자막 가져오기 비활성화
        // 경쟁 영상 저장 성공 후 자막 자동 조회 및 저장
        // const videoIds = data.videos.map((v: VideoItem) => v.video_id)
        // return fetchSubtitles({ video_ids: videoIds, languages: ["ko", "en"] })
      })
      .catch(console.error)
  }, [data])

  // VideoItem을 UI 형식으로 변환
  const competitorVideos = data?.videos.map((video: VideoItem) => ({
    id: video.video_id,
    channel: video.channel_title,
    title: video.title,
    thumbnail: video.thumbnail_url,
    views: formatNumber(video.statistics.view_count),
    likes: formatNumber(video.statistics.like_count),
    comments: formatNumber(video.statistics.comment_count),
    url: `https://www.youtube.com/watch?v=${video.video_id}`,
    popularity_score: video.popularity_score,
    days_since_upload: video.days_since_upload,
    description: video.description,
    published_at: new Date(video.published_at).toLocaleDateString('ko-KR')
  })) || []

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg">경쟁 영상 분석</CardTitle>
            {data && (
              <Badge variant="secondary" className="text-xs">
                {data.total_results}개
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              트렌드 점수 기준
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading}
              className="h-7 w-7 p-0"
            >
              <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
        {data && (
          <div className="mt-2 text-xs text-muted-foreground">
            검색어: <span className="font-medium">{data.query}</span>
          </div>
        )}
      </CardHeader>
      <CardContent>
        {/* 로딩 상태 */}
        {isLoading && (
          <div className="flex items-center justify-center h-[400px]">
            <div className="text-center space-y-3">
              <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
              <p className="text-sm text-muted-foreground">
                YouTube에서 경쟁 영상을 분석하고 있습니다...
              </p>
            </div>
          </div>
        )}

        {/* 에러 상태 */}
        {isError && (
          <div className="flex items-center justify-center h-[400px]">
            <div className="text-center space-y-3">
              <AlertCircle className="w-8 h-8 text-destructive mx-auto" />
              <p className="text-sm text-muted-foreground">
                영상을 불러오는 중 오류가 발생했습니다.
              </p>
              <p className="text-xs text-muted-foreground">
                {error instanceof Error ? error.message : '알 수 없는 오류'}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                className="mt-2"
              >
                <RefreshCw className="w-3 h-3 mr-1" />
                다시 시도
              </Button>
            </div>
          </div>
        )}

        {/* 데이터 표시 */}
        {!isLoading && !isError && competitorVideos.length === 0 && (
          <div className="flex items-center justify-center h-[400px]">
            <div className="text-center space-y-2">
              <AlertCircle className="w-8 h-8 text-muted-foreground mx-auto" />
              <p className="text-sm text-muted-foreground">
                검색 결과가 없습니다.
              </p>
            </div>
          </div>
        )}

        {!isLoading && !isError && competitorVideos.length > 0 && (
          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-4">
              {competitorVideos.map((video, index) => (
                <div
                  key={video.id}
                  className="rounded-lg border border-border/50 overflow-hidden bg-muted/20 relative"
                >
                  {/* Ranking Badge */}
                  <div className="absolute top-2 left-2 z-10">
                    <Badge
                      variant={index === 0 ? "default" : "secondary"}
                      className="text-xs font-bold"
                    >
                      #{index + 1}
                    </Badge>
                  </div>

                  {/* Video Preview */}
                  <div className="flex gap-3 p-3">
                    {/* Thumbnail */}
                    <a
                      href={video.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="relative w-32 h-20 rounded-lg overflow-hidden flex-shrink-0 group cursor-pointer"
                    >
                      <img
                        src={video.thumbnail}
                        alt={video.title}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-black/20 group-hover:bg-black/10 transition-colors flex items-center justify-center">
                        <Play className="w-8 h-8 text-white group-hover:scale-110 transition-transform" />
                      </div>
                    </a>

                    <div className="flex-1 min-w-0">
                      <a
                        href={video.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-sm text-foreground hover:text-primary transition-colors line-clamp-2 flex items-start gap-1"
                      >
                        {video.title}
                        <ExternalLink className="w-3 h-3 flex-shrink-0 mt-0.5" />
                      </a>
                      <p className="text-xs text-muted-foreground mt-1">{video.channel}</p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground flex-wrap">
                        <div className="flex items-center gap-1">
                          <Eye className="w-3 h-3" />
                          {video.views}
                        </div>
                        <div className="flex items-center gap-1">
                          <ThumbsUp className="w-3 h-3" />
                          {video.likes}
                        </div>
                        <div className="flex items-center gap-1">
                          <MessageSquare className="w-3 h-3" />
                          {video.comments}
                        </div>
                        <div className="flex items-center gap-1">
                          <TrendingUp className="w-3 h-3 text-primary" />
                          <span className="font-medium text-primary">
                            {video.popularity_score.toFixed(0)}점
                          </span>
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {video.published_at} ({video.days_since_upload}일 전)
                      </div>
                    </div>
                  </div>

                  {/* Analysis Toggle */}
                  <Button
                    variant="ghost"
                    className="w-full rounded-none border-t border-border/50 h-8 text-xs text-muted-foreground hover:text-foreground"
                    onClick={() => setExpandedId(expandedId === video.id ? null : video.id)}
                  >
                    상세 정보 보기
                    {expandedId === video.id ? (
                      <ChevronUp className="w-4 h-4 ml-1" />
                    ) : (
                      <ChevronDown className="w-4 h-4 ml-1" />
                    )}
                  </Button>

                  {/* Expanded Details */}
                  {expandedId === video.id && (
                    <ExpandedVideoDetails video={video} videoId={video.id} />
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>

        )}
      </CardContent>
    </Card>
  )
}

function ExpandedVideoDetails({
  video,
  videoId,
}: {
  video: { url: string; description?: string; popularity_score: number; days_since_upload: number }
  videoId: string
}) {
  const { data: analysis, isLoading, isError, error } = useQuery({
    queryKey: ['video-analysis', videoId],
    queryFn: () => analyzeVideoContent(videoId),
    enabled: !!videoId,
  })

  return (
    <div className="p-4 border-t border-border/50 bg-muted/30 space-y-3">
      {isLoading && (
        <div className="flex items-center gap-2 py-4">
          <Loader2 className="w-4 h-4 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">영상 내용 분석 중...</span>
        </div>
      )}
      {isError && (
        <div className="text-sm text-destructive py-2">
          {(error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
            '자막을 사용할 수 없어 분석할 수 없습니다.'}
        </div>
      )}
      {analysis && (
        <>
          <div>
            <div className="text-sm font-medium mb-1">핵심 내용</div>
            <p className="text-xs text-muted-foreground">{analysis.summary}</p>
          </div>
          {analysis.strengths.length > 0 && (
            <div>
              <div className="text-sm font-medium mb-1">장점</div>
              <ul className="text-xs text-muted-foreground space-y-0.5 list-disc list-inside">
                {analysis.strengths.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {analysis.weaknesses.length > 0 && (
            <div>
              <div className="text-sm font-medium mb-1">부족한 점</div>
              <ul className="text-xs text-muted-foreground space-y-0.5 list-disc list-inside">
                {analysis.weaknesses.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
      <div>
        <div className="text-sm font-medium mb-1">영상 설명</div>
        <p className="text-xs text-muted-foreground line-clamp-4">
          {video.description || '설명이 없습니다.'}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 pt-2 border-t border-border/50">
        <div>
          <div className="text-xs text-muted-foreground mb-1">일일 조회수</div>
          <div className="text-sm font-medium">
            {formatNumber(Math.floor(video.popularity_score / (1 + Math.max(0, (30 - video.days_since_upload) / 30))))}
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-1">트렌드 점수</div>
          <div className="text-sm font-medium text-primary">
            {video.popularity_score.toFixed(2)}
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-1">신선도</div>
          <div className="text-sm font-medium">
            {video.days_since_upload <= 30
              ? `${(1 + (30 - video.days_since_upload) / 30).toFixed(2)}x`
              : '1.0x'}
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-1">참여도</div>
          <div className="text-sm font-medium">
            {formatNumber(video.popularity_score - Math.floor(video.popularity_score / (1 + Math.max(0, (30 - video.days_since_upload) / 30))))}
          </div>
        </div>
      </div>
      <Button variant="outline" size="sm" className="w-full mt-2" asChild>
        <a href={video.url} target="_blank" rel="noopener noreferrer">
          <ExternalLink className="w-3 h-3 mr-1" />
          YouTube에서 보기
        </a>
      </Button>
    </div>
  )
}
