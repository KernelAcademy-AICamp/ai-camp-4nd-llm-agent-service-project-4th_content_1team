import { useState } from "react"
import { useSidebar } from "../contexts/sidebar-context"
import { Home, FileText, BarChart3, Menu, ChevronRight, Sparkles } from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import { cn } from "../lib/utils"
import { Button } from "./ui/button"
import { Badge } from "./ui/badge"
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

// 메뉴 아이템 타입
interface MenuItem {
  path: string
  label: string
  icon: React.ElementType
  badge?: string
  submenu?: SubMenuItem[]
}

interface SubMenuItem {
  id: string
  title: string
  description: string
}

// 메뉴 데이터
const menuItems: MenuItem[] = [
  { 
    path: "/explore", 
    label: "주제 탐색", 
    icon: Home 
  },
  {
    path: "/script",
    label: "스크립트 작성",
    icon: FileText,
    badge: "2",
    submenu: [
      {
        id: "1",
        title: "SNOW",
        description: "카메라 서비스 기획(SODA, Foodie..."
      },
      {
        id: "2",
        title: "SNOW",
        description: "카메라 서비스 기획(SODA, Foodie..."
      }
    ]
  },
  {
    path: "/analysis",
    label: "채널 분석",
    icon: BarChart3
  },
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
    <aside
      className={cn(
        "h-full bg-[#050609] border-r border-border/50 transition-all duration-300 flex flex-col",
        isAppSidebarOpen ? "w-64" : "w-16"
      )}
    >
      {/* 헤더: 로고 + 프로필 */}
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center justify-between">
          {/* 로고 (펼쳤을 때만) */}
          {isAppSidebarOpen && (
            <div className="h-[34px] w-[162px]">
              <img 
                src="/creatorhub-logo.png" 
                alt="CreatorHub" 
                className="h-full w-full object-contain"
              />
            </div>
          )}
          
          {/* 프로필 아이콘 */}
          <button
            onClick={toggleAppSidebar}
            className="p-2 hover:bg-white/10 rounded-md transition-colors"
            aria-label="Toggle sidebar"
          >
            <Menu className="w-5 h-5 text-white" />
          </button>
        </div>
      </div>

      {/* 메뉴 아이템 */}
      <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
        {menuItems.map((item) => (
          <MenuItemComponent
            key={item.path}
            item={item}
            isCollapsed={!isAppSidebarOpen}
          />
        ))}
      </nav>

      {/* 하단: 사용자 정보 + 업그레이드 */}
      <div className="border-t border-[#8c929d]/30 pt-4">
        {/* 사용자 정보 */}
        {isAppSidebarOpen && (
          <div className="px-4 pb-3">
            <div className="flex items-center gap-3">
              <Avatar className="w-[34px] h-[34px] flex-shrink-0">
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
                <div className="flex items-center gap-2 min-w-0">
                  <p 
                    className="text-sm font-semibold text-white truncate" 
                    title={displayName}
                  >
                    {nameTruncated}
                  </p>
                  <Badge 
                    variant="secondary" 
                    className="bg-[#f3ffc7] text-[#6e8b00] text-xs px-2 flex-shrink-0"
                  >
                    스타터
                  </Badge>
                </div>
                <p 
                  className="text-xs text-[#8c929d] truncate" 
                  title={displayEmail || undefined}
                >
                  {emailTruncated}
                </p>
              </div>
            </div>
          </div>
        )}
        
        {/* 업그레이드 버튼 */}
        <div className="px-4 pb-4">
          <Button
            className={cn(
              "w-full bg-primary hover:bg-primary/90 text-white",
              !isAppSidebarOpen && "px-0"
            )}
          >
            {isAppSidebarOpen ? (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                플랜 업그레이드
              </>
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </aside>
  )
}

// 메뉴 아이템 컴포넌트
function MenuItemComponent({ 
  item, 
  isCollapsed 
}: { 
  item: MenuItem
  isCollapsed: boolean 
}) {
  const location = useLocation()
  const isActive = location.pathname.startsWith(item.path)
  const [isExpanded, setIsExpanded] = useState(false)
  const Icon = item.icon
  
  const hasSubmenu = item.submenu && item.submenu.length > 0
  
  return (
    <div>
      {/* 메인 메뉴 */}
      <Link
        to={item.path}
        className={cn(
          "flex items-center gap-3 px-3 py-3 rounded-lg transition-colors relative",
          isActive 
            ? "bg-[#131520] text-white" 
            : "text-[#8c929d] hover:bg-white/5 hover:text-white"
        )}
        onClick={() => hasSubmenu && setIsExpanded(!isExpanded)}
        title={isCollapsed ? item.label : undefined}
      >
        <Icon className="w-5 h-5 flex-shrink-0" />
        
        {!isCollapsed && (
          <>
            <span className="text-sm font-medium flex-1">
              {item.label}
            </span>
            
            {/* Badge */}
            {item.badge && (
              <Badge 
                variant="secondary" 
                className="bg-[#6b7280] text-white text-xs px-1.5 py-0"
              >
                {item.badge}
              </Badge>
            )}
            
            {/* Submenu 화살표 */}
            {hasSubmenu && (
              <ChevronRight 
                className={cn(
                  "w-4 h-4 transition-transform",
                  isExpanded && "rotate-90"
                )}
              />
            )}
          </>
        )}
      </Link>
      
      {/* Submenu */}
      {hasSubmenu && isExpanded && !isCollapsed && (
        <div className="mt-1 ml-12 space-y-1">
          {item.submenu!.map((sub) => (
            <Link
              key={sub.id}
              to={`${item.path}/${sub.id}`}
              className="block px-3 py-2 rounded-md hover:bg-white/5 transition-colors"
            >
              <p className="text-sm font-semibold text-white truncate">
                {sub.title}
              </p>
              <p className="text-xs text-[#8c929d] truncate mt-0.5">
                {sub.description}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

