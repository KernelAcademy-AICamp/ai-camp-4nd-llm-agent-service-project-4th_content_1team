import { useSidebar } from "../contexts/sidebar-context"
import { Compass, FileText, BarChart3, PanelLeft, Crown, Play } from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import { cn } from "../lib/utils"
import { Button } from "./ui/button"
import { Avatar, AvatarFallback } from "./ui/avatar"

const menuItems = [
  { path: "/explore", label: "주제 탐색", icon: Compass },
  { path: "/script", label: "스크립트 작성", icon: FileText },
  { path: "/analysis", label: "채널 분석", icon: BarChart3 },
]

// 사용자 정보 (실제로는 Context에서 가져와야 함)
const userInfo = {
  name: "Doheun Lee",
  email: "battingeye.cs@gmail.com",
  plan: "스타터",
}

export function AppSidebar() {
  const { isAppSidebarOpen, toggleAppSidebar } = useSidebar()
  const location = useLocation()

  if (!isAppSidebarOpen) {
    return null
  }

  return (
    <>
      {/* 오버레이 배경 (모바일/태블릿에서만) */}
      <div 
        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        onClick={toggleAppSidebar}
        aria-hidden="true"
      />
      
      {/* 사이드바 */}
      <aside className={cn(
        "h-full w-[300px] bg-black border-r border-[#131520] flex flex-col",
        "lg:relative", // Desktop: 일반 레이아웃
        "fixed z-50 inset-y-0 left-0" // Tablet/Mobile: 오버레이
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
              <Avatar className="w-[40px] h-[40px]">
                <AvatarFallback className="bg-[#6b7280] text-white text-sm">
                  {userInfo.name.split(' ').map(n => n[0]).join('')}
                </AvatarFallback>
              </Avatar>
              
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate mb-0.5">
                  {userInfo.name}
                </p>
                <p className="text-xs text-[#8c929d] truncate">
                  {userInfo.email}
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
              <AvatarFallback className="bg-[#6b7280] text-white text-xs">
                {userInfo.name.split(' ').map(n => n[0]).join('')}
              </AvatarFallback>
            </Avatar>
          </button>
        </div>
      )}
    </aside>
    </>
  )
}
