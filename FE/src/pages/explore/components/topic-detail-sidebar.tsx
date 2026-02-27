import { X } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "../../../components/ui/button"
import { Badge } from "../../../components/ui/badge"
import { useSidebar } from "../../../contexts/sidebar-context"
import { cn } from "../../../lib/utils"
import type { DisplayTopic } from "../page"

interface TopicDetailSidebarProps {
  topic: DisplayTopic
}

// 뱃지별 색상 매핑 (topic-card.tsx와 통일)
const BADGE_COLORS: Record<string, string> = {
  "성공 방정식": "bg-[#dcfce8] text-[#2a8849]",
  "구독자 관심": "bg-[#dbeafe] text-[#1e40af]",
  "최근 경향성": "bg-[#f3e8ff] text-[#6b21a8]",
  "차별화 기회": "bg-[#fef3c7] text-[#d97706]",
}

export function TopicDetailSidebar({ topic }: TopicDetailSidebarProps) {
  const { closeDetailSidebar } = useSidebar()

  const badgeColor = BADGE_COLORS[topic.badge] || "bg-muted text-muted-foreground"

  // 스크립트 작성 링크
  const scriptLink = `/script/edit?topic=${encodeURIComponent(topic.title)}&topicId=${topic.id}&topicType=${topic.topic_type || 'trend'}`

  return (
    <div className="fixed right-0 top-0 h-full w-[400px] bg-card border-l border-border shadow-lg z-50 overflow-y-auto">
      {/* 헤더 */}
      <div className="sticky top-0 bg-card border-b border-border p-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">주제 상세</h2>
        <button
          onClick={closeDetailSidebar}
          className="p-2 hover:bg-muted rounded-md transition-colors"
          aria-label="닫기"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* 내용 */}
      <div className="p-6 space-y-6">
        {/* 뱃지 */}
        <Badge
          variant="secondary"
          className={cn("text-sm font-medium", badgeColor)}
        >
          {topic.badge}
        </Badge>

        {/* 제목 */}
        <div>
          <h3 className="text-xl font-bold text-foreground mb-3">
            {topic.title}
          </h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {topic.description}
          </p>
        </div>

        {/* 추천 방향 */}
        {topic.recommendation_direction && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-foreground">추천 방향</h4>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {topic.recommendation_direction}
            </p>
          </div>
        )}

        {/* 콘텐츠 접근 각도 */}
        {topic.content_angles.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-foreground">콘텐츠 접근 각도</h4>
            <ul className="space-y-1.5">
              {topic.content_angles.map((angle, index) => (
                <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-primary mt-0.5">&#8226;</span>
                  <span>{angle}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 트렌드 근거 */}
        {topic.trend_basis && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-foreground">트렌드 근거</h4>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {topic.trend_basis}
            </p>
          </div>
        )}

        {/* 썸네일 아이디어 */}
        {topic.thumbnail_idea && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-foreground">썸네일 아이디어</h4>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {topic.thumbnail_idea}
            </p>
          </div>
        )}

        {/* 해시태그 */}
        {topic.hashtags.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground">관련 키워드</h4>
            <div className="flex flex-wrap gap-2">
              {topic.hashtags.map((tag, index) => (
                <Badge key={index} variant="outline" className="text-xs">
                  #{tag}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* 스크립트 생성 버튼 */}
        <Link to={scriptLink} onClick={closeDetailSidebar}>
          <Button
            className="w-full bg-primary hover:bg-primary/90"
            size="lg"
          >
            이 주제로 스크립트 작성
          </Button>
        </Link>
      </div>
    </div>
  )
}
