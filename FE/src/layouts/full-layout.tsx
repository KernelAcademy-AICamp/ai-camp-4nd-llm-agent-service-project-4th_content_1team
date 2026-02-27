import { ReactNode } from "react"
import { useSidebar } from "../contexts/sidebar-context"
import { AppSidebar } from "../components/app-sidebar"
import { AppHeader } from "../components/app-header"
import { cn } from "../lib/utils"

interface FullLayoutProps {
  children: ReactNode
  breadcrumb?: string
  actions?: ReactNode
}

export function FullLayout({ children, breadcrumb, actions }: FullLayoutProps) {
  const { isDetailSidebarOpen, isAppSidebarOpen } = useSidebar()

  return (
    <div className="flex h-screen">
      {/* 왼쪽: AppSidebar */}
      <AppSidebar />

      {/* 가운데: Header + Main */}
      <div
        className={cn(
          "flex-1 flex flex-col transition-all duration-300 ease-in-out",
          // AppSidebar 열릴 때 왼쪽 공간 확보
          isAppSidebarOpen ? "ml-[300px]" : "ml-0",
          // DetailSidebar 열릴 때 우측 공간 확보
          isDetailSidebarOpen && "mr-[400px]"
        )}
      >
        {/* 헤더 */}
        <AppHeader breadcrumb={breadcrumb} actions={actions} />

        {/* 메인 콘텐츠 */}
        <main className="flex-1 overflow-y-auto bg-background">
          {children}
        </main>
      </div>
    </div>
  )
}
