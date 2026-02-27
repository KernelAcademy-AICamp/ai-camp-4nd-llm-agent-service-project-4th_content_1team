import { useSidebar } from "@/contexts/sidebar-context"
import { Compass, FileText, BarChart3, PanelLeft, Crown } from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"

const menuItems = [
  { path: "/explore", label: "주제 탐색", icon: Compass },
  { path: "/script", label: "스크립트 작성", icon: FileText },
  { path: "/analysis", label: "채널 분석", icon: BarChart3 },
]

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
    <aside className="h-full w-[300px] bg-black border-r border-[#131520] flex flex-col">
      <div className="h-[66px] px-4 border-b border-[#131520] flex items-center">
        <div className="flex items-center justify-between w-full">
          <img
            src="/images/creatorhub-logo.png"
            alt="CreatorHub"
            className="h-[34px] w-[162px] object-contain"
          />
          <button
            onClick={toggleAppSidebar}
            className="p-2 hover:bg-white/10 rounded-md transition-colors"
            aria-label="Close sidebar"
          >
            <PanelLeft className="w-5 h-5 text-white" />
          </button>
        </div>
      </div>

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
              {isAppSidebarOpen && (
                <span className="text-base font-medium">{item.label}</span>
              )}
            </Link>
          )
        })}
      </nav>

      {isAppSidebarOpen && (
        <div className="border-t border-[#131520] pt-4">
          <div className="px-4 pb-3">
            <div className="flex items-center gap-3">
              <Avatar className="w-[40px] h-[40px]">
                <AvatarFallback className="bg-[#6b7280] text-white text-sm">
                  {userInfo.name.split(" ").map((n) => n[0]).join("")}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate mb-0.5">
                  {userInfo.name}
                </p>
                <p className="text-xs text-[#8c929d] truncate">{userInfo.email}</p>
              </div>
            </div>
          </div>
          <div className="px-4 pb-4">
            <Button className="w-full bg-primary hover:bg-primary/90 text-white font-semibold">
              <Crown className="w-4 h-4 mr-2" />
              플랜 업그레이드
            </Button>
          </div>
        </div>
      )}

      {!isAppSidebarOpen && (
        <div className="p-2">
          <button
            onClick={toggleAppSidebar}
            className="w-full p-2 hover:bg-white/10 rounded-md transition-colors"
            title="프로필"
          >
            <Avatar className="w-8 h-8 mx-auto">
              <AvatarFallback className="bg-[#6b7280] text-white text-xs">
                {userInfo.name.split(" ").map((n) => n[0]).join("")}
              </AvatarFallback>
            </Avatar>
          </button>
        </div>
      )}
    </aside>
  )
}
