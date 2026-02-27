import { useSidebar } from "../contexts/sidebar-context"
import { Compass, FileText, BarChart3, PanelLeft, Crown } from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import { cn } from "../lib/utils"
import { Button } from "./ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar"
import { useAuth } from "../hooks/useAuth"

const EMAIL_TRUNCATE_LEN = 24
const NAME_TRUNCATE_LEN = 14

function truncateEmail(email: string): string {
  if (!email) return ""
  if (email.length <= EMAIL_TRUNCATE_LEN) return email
  return email.slice(0, EMAIL_TRUNCATE_LEN - 3) + "..."
}

function truncateName(name: string): string {
  if (!name) return ""
  if (name.length <= NAME_TRUNCATE_LEN) return name
  return name.slice(0, NAME_TRUNCATE_LEN - 2) + "…"
}

const menuItems = [
  { path: "/explore", label: "주제 탐색", icon: Compass },
  { path: "/script", label: "스크립트 작성", icon: FileText },
  { path: "/analysis", label: "채널 분석", icon: BarChart3 },
]

export function AppSidebar() {
  const { isAppSidebarOpen, toggleAppSidebar } = useSidebar()
  const location = useLocation()
  const { user } = useAuth()

  const displayName = user?.name ?? "사용자"
  const displayEmail = user?.email ?? ""
  const nameTruncated = truncateName(displayName)
  const emailTruncated = truncateEmail(displayEmail)
  const profileImageSrc = user?.avatar_url || "/profile_dummy.png"

  return (
    <>
      {/* 오버레이 배경 (모바일/태블릿에서만) */}
      <div 
        className={cn(
          "fixed inset-0 bg-black/50 z-40 lg:hidden transition-opacity duration-300",
          isAppSidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={toggleAppSidebar}
        aria-hidden="true"
      />
      
      {/* 사이드바 */}
      <aside className={cn(
        "h-full w-[300px] bg-black border-r border-[#131520] flex flex-col",
        "fixed z-50 inset-y-0 left-0",
        "transition-transform duration-300 ease-in-out",
        isAppSidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
      {/* 상단: 로고 + 토글 */}
      <div className="h-[66px] px-4 border-b border-[#131520] flex items-center">
        <div className="flex items-center justify-between w-full">
          {/* 로고 */}
          <img 
            src="/images/creatorhub-logo.png" 
            alt="CreatorHub"
            className="h-[34px] w-[162px] object-contain"
          />
          
          {/* 토글 버튼 */}
          <button
            onClick={toggleAppSidebar}
            className="p-2 hover:bg-white/10 rounded-md transition-colors"
            aria-label="Close sidebar"
          >
            <PanelLeft className="w-5 h-5 text-white" />
          </button>
        </div>
      </div>

      {/* 메뉴 아이템 */}
      <nav className="flex-1 p-4 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname.startsWith(item.path)

          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-3 rounded-lg transition-colors",
                isActive 
                  ? "bg-[#131520] text-white" 
                  : "text-[#8c929d] hover:bg-white/5 hover:text-white"
              )}
              title={!isAppSidebarOpen ? item.label : undefined}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />

              {/* 텍스트는 펼쳤을 때만 */}
              {isAppSidebarOpen && (
                <span className="text-base font-medium">{item.label}</span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* 하단: 사용자 정보 + 업그레이드 */}
      {isAppSidebarOpen && (
        <div className="border-t border-[#131520] pt-4">
          {/* 사용자 프로필 */}
          <div className="px-4 pb-3">
            <div className="flex items-center gap-3">
              <Avatar className="w-[40px] h-[40px] flex-shrink-0">
                <AvatarImage
                  src={profileImageSrc}
                  alt={displayName}
                  onError={(e) => {
                    const target = e.currentTarget
                    if (target.src !== "/profile_dummy.png") {
                      target.src = "/profile_dummy.png"
                    }
                  }}
                />
                <AvatarFallback className="bg-[#6b7280] text-white text-sm">
                  {displayName.slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate mb-0.5" title={displayName}>
                  {nameTruncated}
                </p>
                <p className="text-xs text-[#8c929d] truncate" title={displayEmail || undefined}>
                  {emailTruncated}
                </p>
              </div>
            </div>
          </div>
          
          {/* 업그레이드 버튼 */}
          <div className="px-4 pb-4">
            <Button
              className="w-full bg-primary hover:bg-primary/90 text-white font-semibold"
            >
              <Crown className="w-4 h-4 mr-2" />
              플랜 업그레이드
            </Button>
          </div>
        </div>
      )}
      
      {/* 접힌 상태일 때 하단 */}
      {!isAppSidebarOpen && (
        <div className="p-2">
          <button
            onClick={toggleAppSidebar}
            className="w-full p-2 hover:bg-white/10 rounded-md transition-colors"
            title="프로필"
          >
            <Avatar className="w-8 h-8 mx-auto">
              <AvatarImage src={profileImageSrc} alt={displayName} />
              <AvatarFallback className="bg-[#6b7280] text-white text-xs">
                {displayName.slice(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
          </button>
        </div>
      )}
    </aside>
    </>
  )
}
