import { ReactNode } from "react"
import { useSidebar } from "../contexts/sidebar-context"
import { PanelLeft } from "lucide-react"

interface AppHeaderProps {
  breadcrumb?: string
  actions?: ReactNode
}

export function AppHeader({ breadcrumb, actions }: AppHeaderProps) {
  const { isAppSidebarOpen, toggleAppSidebar } = useSidebar()

  return (
    <header className="h-[66px] bg-card border-b border-border flex items-center px-4">
      <div className="flex items-center justify-between w-full">
        {/* 왼쪽: 토글 버튼 + Breadcrumb */}
        <div className="flex items-center gap-4">
          {/* 토글 버튼 (Sidebar 접힌 상태일 때만) */}
          {!isAppSidebarOpen && (
            <button
              onClick={toggleAppSidebar}
              className="p-2 hover:bg-white/10 rounded-md transition-colors"
              aria-label="Open sidebar"
            >
              <PanelLeft className="w-5 h-5 text-foreground" />
            </button>
          )}
          
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {breadcrumb || (
              <>
                <span>내 채널</span>
                <span>/</span>
                <span>내 채널</span>
              </>
            )}
          </div>
        </div>

        {/* 오른쪽: 액션 버튼 (페이지별 커스텀) */}
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </header>
  )
}
