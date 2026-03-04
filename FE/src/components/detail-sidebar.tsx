import { ReactNode } from "react"
import { useSidebar } from "../contexts/sidebar-context"
import { X } from "lucide-react"
import { cn } from "../lib/utils"
import { Button } from "./ui/button"

interface DetailSidebarProps {
  children: ReactNode
  title?: string
}

export function DetailSidebar({ children, title }: DetailSidebarProps) {
  const { isDetailSidebarOpen, closeDetailSidebar } = useSidebar()

  return (
    <>
      {/* 오버레이 */}
      {isDetailSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={closeDetailSidebar}
        />
      )}

      {/* 우측 슬라이드 패널 */}
      <aside
        className={cn(
          "fixed right-0 top-0 h-full w-[400px] bg-[#ff69b4]/50 backdrop-blur-sm z-50 transition-transform duration-300 shadow-2xl",
          isDetailSidebarOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div className="h-full flex flex-col">
          {/* 헤더 */}
          <div className="h-16 px-6 flex items-center justify-between border-b border-border/50">
            {title && <h3 className="text-lg font-semibold">{title}</h3>}
            <Button
              variant="ghost"
              size="icon"
              onClick={closeDetailSidebar}
              className="ml-auto"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* 콘텐츠 */}
          <div className="flex-1 overflow-y-auto p-6">
            {children}
          </div>
        </div>
      </aside>
    </>
  )
}
