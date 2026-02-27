import { useNavigate } from "react-router-dom"
import { Bookmark } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface TopicCardProps {
  id: string
  badge: string
  title: string
  description: string
  hashtags: string[]
  onClick?: () => void
}

const BADGE_STYLES = {
  "성공 방정식": {
    bar: "bg-gradient-to-b from-[#46da7d] to-[#19a74e]",
    badge: "bg-[#dcfce8] text-[#2a8849]",
  },
  "구독자 관심": {
    bar: "bg-gradient-to-b from-[#3b82f6] to-[#1d4ed8]",
    badge: "bg-[#dbeafe] text-[#1e40af]",
  },
  "최근 경향성": {
    bar: "bg-gradient-to-b from-[#a855f7] to-[#7e22ce]",
    badge: "bg-[#f3e8ff] text-[#6b21a8]",
  },
  "차별화 기회": {
    bar: "bg-gradient-to-b from-[#fbbf24] to-[#f59e0b]",
    badge: "bg-[#fef3c7] text-[#d97706]",
  },
} as const

export function TopicCard({
  id,
  badge,
  title,
  description,
  hashtags,
  onClick,
}: TopicCardProps) {
  const navigate = useNavigate()
  const badgeStyle = BADGE_STYLES[badge as keyof typeof BADGE_STYLES] ?? BADGE_STYLES["성공 방정식"]

  const handleViewDetail = (e: React.MouseEvent) => {
    e.stopPropagation()
    onClick?.()
  }

  const handleCreateScript = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigate(`/script/edit?topic=${encodeURIComponent(title)}`)
  }

  const handleBookmark = (e: React.MouseEvent) => {
    e.stopPropagation()
    console.log("북마크:", id)
    // TODO: 북마크 토글
  }

  return (
    <div className="relative w-full h-[282px] rounded-[10px] overflow-hidden">
      <div className={cn("absolute left-0 top-0 bottom-0 w-1 rounded-l-[10px]", badgeStyle.bar)} />
      <div className="absolute left-1 top-0 right-0 bottom-0 bg-[#1e293b] rounded-r-[10px] flex flex-col">
        <div className="flex-1 px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className={cn("h-[23px] px-2.5 rounded-[3px] flex items-center", badgeStyle.badge)}>
                <span className="text-xs font-medium leading-none">{badge}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-[2px] h-[2px] rounded-full bg-[#9da3af]" />
                <span className="text-xs font-medium text-[#9da3af]">AI 추천</span>
              </div>
            </div>
            <button
              onClick={handleBookmark}
              className="w-5 h-5 flex items-center justify-center text-[#9da3af] hover:text-white transition-colors"
              aria-label="북마크"
            >
              <Bookmark className="w-4 h-4" />
            </button>
          </div>
          <h3 className="text-base font-bold text-white mb-2 line-clamp-2 leading-[1.4]">{title}</h3>
          <p className="text-sm font-medium text-[#8c9bb0] leading-[1.4] line-clamp-2">{description}</p>
        </div>
        <div className="px-4 pb-3 flex items-center gap-1.5 flex-wrap">
          {hashtags.map((tag, index) => (
            <span key={index} className="text-xs text-[#8c9bb0] tracking-tight">
              #{tag}
            </span>
          ))}
        </div>
        <div className="h-[68px] px-4 flex items-center gap-2">
          <Button
            variant="secondary"
            className="flex-1 h-10 bg-[#374151] hover:bg-[#4b5563] text-white text-sm font-medium rounded-lg"
            onClick={handleViewDetail}
          >
            상세내용 보기
          </Button>
          <Button
            className="flex-1 h-10 bg-[#6b27d9] hover:bg-[#5b21b6] text-white text-sm font-medium rounded-lg"
            onClick={handleCreateScript}
          >
            스크립트 작성
          </Button>
        </div>
      </div>
    </div>
  )
}
