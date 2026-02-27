import type { ReactNode } from "react"
import { useSidebar } from "@/contexts/sidebar-context"
import { AppSidebar } from "@/components/app-sidebar"
import { AppHeader } from "@/components/app-header"
import { cn } from "@/lib/utils"

interface FullLayoutProps {
  children: ReactNode
  breadcrumb?: ReactNode
  actions?: ReactNode
}

export function FullLayout({ children, breadcrumb, actions }: FullLayoutProps) {
  const { isDetailSidebarOpen } = useSidebar()

  return (
    <div className="flex h-screen">
      <AppSidebar />
      <div
        className={cn(
          "flex-1 flex flex-col transition-all duration-300 min-w-0",
          isDetailSidebarOpen && "mr-[400px]"
        )}
      >
        <AppHeader breadcrumb={breadcrumb} actions={actions} />
        <main className="flex-1 overflow-y-auto bg-background">{children}</main>
      </div>
    </div>
  )
}
