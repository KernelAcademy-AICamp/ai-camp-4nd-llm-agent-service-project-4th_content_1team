import { X } from "lucide-react"
import { Button } from "../../../components/ui/button"
import { Badge } from "../../../components/ui/badge"
import { useSidebar } from "../../../contexts/sidebar-context"
import { cn } from "../../../lib/utils"

interface TopicDetailSidebarProps {
  topic: {
    id: string
    badge: string
    title: string
    description: string
    hashtags: string[]
  }
}

export function TopicDetailSidebar({ topic }: TopicDetailSidebarProps) {
  const { closeDetailSidebar } = useSidebar()

  // 뱃지 타입 결정
  const isGrowthType = topic.badge === "성공 방정식"

  // 스크립트 생성 핸들러
  const handleCreateScript = () => {
    console.log("스크립트 작성:", topic.id)
    // TODO: 스크립트 생성 페이지로 이동
  }

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
          className={cn(
            "text-sm font-medium",
            isGrowthType 
              ? "bg-green-50 text-green-700" 
              : "bg-amber-50 text-amber-700"
          )}
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

        {/* 해시태그 */}
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

        {/* 스크립트 생성 버튼 */}
        <Button
          onClick={handleCreateScript}
          className="w-full bg-primary hover:bg-primary/90"
          size="lg"
        >
          이 주제로 스크립트 작성
        </Button>
      </div>
    </div>
  )
}
