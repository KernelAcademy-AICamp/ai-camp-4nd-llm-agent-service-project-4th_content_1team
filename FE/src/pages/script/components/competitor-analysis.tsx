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
  CheckCircle,
  ChevronDown,
  ChevronUp
} from "lucide-react"
import { useState } from "react"

const competitorVideos = [
  {
    id: 1,
    channel: "게임왕국",
    title: "2026년 꼭 해야 할 게임 트렌드 TOP 5",
    thumbnail: "bg-gradient-to-br from-primary/40 to-chart-2/40",
    views: "125만",
    likes: "3.2만",
    comments: "1,842",
    duration: "18:24",
    url: "#",
    analysis: {
      summary: "깔끔한 편집과 명확한 전달력으로 시청자 유지율이 높음. 특히 각 트렌드별 실제 게임 플레이 영상을 삽입한 점이 효과적.",
      strengths: [
        "트렌드별 실제 게임 플레이 영상 삽입",
        "간결하고 명확한 설명",
        "매력적인 썸네일 디자인",
        "챕터 구분이 잘 되어 있음"
      ],
      weaknesses: [
        "인트로가 다소 길어 이탈률 발생",
        "출처 표기가 부족함",
        "후반부 내용이 다소 중복됨"
      ]
    }
  },
  {
    id: 2,
    channel: "테크게이머",
    title: "올해 게임 산업 완전 분석 | AI, 클라우드, 메타버스",
    thumbnail: "bg-gradient-to-br from-chart-3/40 to-chart-4/40",
    views: "89만",
    likes: "2.1만",
    comments: "987",
    duration: "24:15",
    url: "#",
    analysis: {
      summary: "심층적인 분석과 데이터 기반 콘텐츠로 교육적 가치가 높음. 다만 영상 길이가 길어 시청 완료율이 낮을 수 있음.",
      strengths: [
        "데이터 기반의 심층 분석",
        "전문가 인터뷰 포함",
        "그래프와 차트 활용",
        "업계 인사이트 제공"
      ],
      weaknesses: [
        "영상 길이가 다소 김",
        "속도감이 부족함",
        "일반 시청자에게 어려울 수 있음"
      ]
    }
  },
  {
    id: 3,
    channel: "일상게임러",
    title: "게임 유튜버가 말하는 2026년 게임 전망",
    thumbnail: "bg-gradient-to-br from-chart-5/40 to-primary/40",
    views: "67만",
    likes: "1.8만",
    comments: "2,156",
    duration: "12:08",
    url: "#",
    analysis: {
      summary: "개인적인 경험을 바탕으로 한 친근한 톤이 특징. 댓글 참여율이 높아 커뮤니티 형성에 효과적.",
      strengths: [
        "친근하고 편안한 톤",
        "높은 댓글 참여율",
        "적절한 영상 길이",
        "시청자와의 소통 강조"
      ],
      weaknesses: [
        "객관적 데이터 부족",
        "영상 퀄리티가 상대적으로 낮음",
        "구조화가 덜 되어 있음"
      ]
    }
  },
]

export function CompetitorAnalysis() {
  const [expandedId, setExpandedId] = useState<number | null>(1)

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">경쟁 영상 분석</CardTitle>
          <Badge variant="secondary" className="text-xs">
            AI 분석
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-4">
            {competitorVideos.map((video) => (
              <div
                key={video.id}
                className="rounded-lg border border-border/50 overflow-hidden bg-muted/20"
              >
                {/* Video Preview */}
                <div className="flex gap-3 p-3">
                  <div className={`w-32 h-20 rounded-lg ${video.thumbnail} flex items-center justify-center flex-shrink-0 relative group cursor-pointer`}>
                    <Play className="w-8 h-8 text-foreground/80 group-hover:scale-110 transition-transform" />
                    <Badge variant="secondary" className="absolute bottom-1 right-1 text-xs px-1">
                      {video.duration}
                    </Badge>
                  </div>
                  <div className="flex-1 min-w-0">
                    <a
                      href={video.url}
                      className="font-medium text-sm text-foreground hover:text-primary transition-colors line-clamp-2 flex items-start gap-1"
                    >
                      {video.title}
                      <ExternalLink className="w-3 h-3 flex-shrink-0 mt-0.5" />
                    </a>
                    <p className="text-xs text-muted-foreground mt-1">{video.channel}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
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
                    </div>
                  </div>
                </div>

                {/* Analysis Toggle */}
                <Button
                  variant="ghost"
                  className="w-full rounded-none border-t border-border/50 h-8 text-xs text-muted-foreground hover:text-foreground"
                  onClick={() => setExpandedId(expandedId === video.id ? null : video.id)}
                >
                  AI 분석 보기
                  {expandedId === video.id ? (
                    <ChevronUp className="w-4 h-4 ml-1" />
                  ) : (
                    <ChevronDown className="w-4 h-4 ml-1" />
                  )}
                </Button>

                {/* Expanded Analysis */}
                {expandedId === video.id && (
                  <div className="p-4 border-t border-border/50 bg-muted/30 space-y-4">
                    <p className="text-sm text-muted-foreground">
                      {video.analysis.summary}
                    </p>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="flex items-center gap-2 text-sm font-medium text-accent mb-2">
                          <CheckCircle className="w-4 h-4" />
                          성공 포인트
                        </div>
                        <ul className="space-y-1">
                          {video.analysis.strengths.map((strength, i) => (
                            <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                              <TrendingUp className="w-3 h-3 text-accent flex-shrink-0 mt-0.5" />
                              {strength}
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div>
                        <div className="flex items-center gap-2 text-sm font-medium text-chart-3 mb-2">
                          <AlertCircle className="w-4 h-4" />
                          개선 포인트
                        </div>
                        <ul className="space-y-1">
                          {video.analysis.weaknesses.map((weakness, i) => (
                            <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                              <AlertCircle className="w-3 h-3 text-chart-3 flex-shrink-0 mt-0.5" />
                              {weakness}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
