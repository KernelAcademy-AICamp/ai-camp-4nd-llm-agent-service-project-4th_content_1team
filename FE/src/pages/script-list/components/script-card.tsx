import { useState } from "react"
import { Badge } from "@/components/ui/badge"

interface ScriptCardProps {
  id: string
  title: string
  created_at: string
  thumbnail?: string
  is_completed?: boolean
  onClick?: () => void
}

function ThumbnailFallback() {
  return (
    <div className="w-full h-full bg-gradient-to-br from-[#6b27d9] to-[#4c1d95] flex items-center justify-center">
      <span className="text-white text-lg font-semibold">CreatorHub</span>
    </div>
  )
}

export function ScriptCard({
  id,
  title,
  created_at,
  thumbnail,
  is_completed = false,
  onClick,
}: ScriptCardProps) {
  const [imageError, setImageError] = useState(false)

  const getImageSource = () => {
    if (thumbnail) return thumbnail
    return "/images/script-dummy.png"
  }

  const handleImageError = () => setImageError(true)

  const handleClick = () => onClick?.()

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, "0")
    const day = String(date.getDate()).padStart(2, "0")
    return `${year}.${month}.${day}`
  }

  return (
    <div
      className="flex flex-col w-full max-w-none md:max-w-[323px] rounded-lg border border-border overflow-hidden hover:shadow-md transition-shadow cursor-pointer bg-card"
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") handleClick()
      }}
    >
      <div className="relative h-[180px] w-full bg-muted">
        {!imageError ? (
          <img
            src={getImageSource()}
            alt={title}
            className="w-full h-full object-cover"
            onError={handleImageError}
          />
        ) : (
          <ThumbnailFallback />
        )}
        {!is_completed && (
          <div className="absolute top-3 right-3">
            <Badge className="bg-gray-500/90 text-white hover:bg-gray-500 font-semibold text-sm px-3 py-1">
              작성 중
            </Badge>
          </div>
        )}
      </div>
      <div className="p-3.5">
        <h3 className="font-medium text-base text-foreground line-clamp-2 mb-2.5 min-h-[44px]">
          {title}
        </h3>
        <p className="text-sm text-muted-foreground">{formatDate(created_at)}</p>
      </div>
    </div>
  )
}
