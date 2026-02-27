import type { ReactNode } from "react"
import { useSidebar } from "@/contexts/sidebar-context"
import { PanelLeft } from "lucide-react"

interface AppHeaderProps {
  breadcrumb?: ReactNode
  actions?: ReactNode
}

export function AppHeader({ breadcrumb, actions }: AppHeaderProps) {
  const { isAppSidebarOpen, toggleAppSidebar } = useSidebar()

  return (
    <header className="h-[66px] bg-card border-b border-border flex items-center px-4 shrink-0">
      <div className="flex items-center justify-between w-full">
        <div className="flex items-center gap-4">
          {!isAppSidebarOpen && (
            <button
              onClick={toggleAppSidebar}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              aria-label="Open sidebar"
            >
              <PanelLeft className="w-5 h-5 text-foreground" />
            </button>
          )}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {breadcrumb ?? (
              <>
                <span>내 채널</span>
                <span>/</span>
                <span>내 채널</span>
              </>
            )}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </header>
  )
}
