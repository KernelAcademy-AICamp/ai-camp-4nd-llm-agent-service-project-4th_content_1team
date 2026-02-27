import { Bookmark } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "../../../components/ui/button"
import { cn } from "../../../lib/utils"

interface TopicCardProps {
  id: string
  badge: string
  title: string
  description: string
  hashtags: string[]
  topicId?: string
  topicType?: string
  onClick?: () => void
  onScriptWrite?: () => void
}

// 뱃지별 색상 매핑
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
  topicId,
  topicType,
  onClick,
  onScriptWrite,
}: TopicCardProps) {
  // 뱃지 스타일 가져오기
  const badgeStyle = BADGE_STYLES[badge as keyof typeof BADGE_STYLES] || BADGE_STYLES["성공 방정식"]

  // 상세 보기 핸들러
  const handleViewDetail = (e: React.MouseEvent) => {
    e.stopPropagation()
    onClick?.()
  }

  // 스크립트 작성 링크
  const scriptLink = topicId
    ? `/script/edit?topic=${encodeURIComponent(title)}&topicId=${topicId}&topicType=${topicType || 'trend'}`
    : undefined

  // 북마크 핸들러
  const handleBookmark = (e: React.MouseEvent) => {
    e.stopPropagation()
    console.log("북마크:", id)
    // TODO: 북마크 토글
  }

  return (
    <div className="relative w-full h-[282px] rounded-[10px] overflow-hidden">
      {/* 왼쪽 컬러 바 */}
      <div className={cn("absolute left-0 top-0 bottom-0 w-1 rounded-l-[10px]", badgeStyle.bar)} />
      
      {/* 메인 콘텐츠 */}
      <div className="absolute left-1 top-0 right-0 bottom-0 bg-[#1e293b] rounded-r-[10px] flex flex-col">
        {/* 상단 콘텐츠 영역 */}
        <div className="flex-1 px-4 py-4">
          {/* 헤더: 뱃지 + AI 추천 + 북마크 */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {/* 뱃지 */}
              <div className={cn("h-[23px] px-2.5 rounded-[3px] flex items-center", badgeStyle.badge)}>
                <span className="text-xs font-medium leading-none">
                  {badge}
                </span>
              </div>
              
              {/* AI 추천 표시 */}
              <div className="flex items-center gap-1">
                <div className="w-[2px] h-[2px] rounded-full bg-[#9da3af]" />
                <span className="text-xs font-medium text-[#9da3af]">AI 추천</span>
              </div>
            </div>
            
            {/* 북마크 버튼 */}
            <button 
              onClick={handleBookmark}
              className="w-5 h-5 flex items-center justify-center text-[#9da3af] hover:text-white transition-colors"
              aria-label="북마크"
            >
              <Bookmark className="w-4 h-4" />
            </button>
          </div>
          
          {/* 제목 */}
          <h3 className="text-base font-bold text-white mb-2 line-clamp-2 leading-[1.4]">
            {title}
          </h3>
          
          {/* 설명 */}
          <p className="text-sm font-medium text-[#8c9bb0] leading-[1.4] line-clamp-2">
            {description}
          </p>
        </div>
        
        {/* 해시태그 (하단 버튼 위) */}
        <div className="px-4 pb-3 flex items-center gap-1.5 flex-wrap">
          {hashtags.map((tag, index) => (
            <span 
              key={index} 
              className="text-xs text-[#8c9bb0] tracking-tight"
            >
              #{tag}
            </span>
          ))}
        </div>
        
        {/* 하단 버튼 영역 */}
        <div className="h-[68px] px-4 flex items-center gap-2">
          <Button 
            variant="secondary"
            className="flex-1 h-10 bg-[#374151] hover:bg-[#4b5563] text-white text-sm font-medium rounded-lg"
            onClick={handleViewDetail}
          >
            상세내용 보기
          </Button>
          {scriptLink ? (
            <Link
              to={scriptLink}
              className="flex-1"
              onClick={(e) => {
                e.stopPropagation()
                onScriptWrite?.()
              }}
            >
              <Button
                className="w-full h-10 bg-[#6b27d9] hover:bg-[#5b21b6] text-white text-sm font-medium rounded-lg"
              >
                스크립트 작성
              </Button>
            </Link>
          ) : (
            <Button
              className="flex-1 h-10 bg-[#6b27d9] hover:bg-[#5b21b6] text-white text-sm font-medium rounded-lg"
              onClick={(e) => e.stopPropagation()}
              disabled
            >
              스크립트 작성
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
