import { ReactNode } from "react"
import { AppHeader } from "../components/app-header"

interface HeaderOnlyLayoutProps {
  children: ReactNode
  breadcrumb?: string
  actions?: ReactNode
}

export function HeaderOnlyLayout({
  children,
  breadcrumb,
  actions,
}: HeaderOnlyLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* 헤더 */}
      <AppHeader breadcrumb={breadcrumb} actions={actions} />

      {/* 메인 콘텐츠 (전체 너비) */}
      <main className="flex-1 bg-[#c5d9a4]">
        {children}
      </main>
    </div>
  )
}
