import type { ReactNode } from "react"
import { AppHeader } from "@/components/app-header"

interface HeaderOnlyLayoutProps {
  children: ReactNode
  breadcrumb?: ReactNode
  actions?: ReactNode
}

export function HeaderOnlyLayout({
  children,
  breadcrumb,
  actions,
}: HeaderOnlyLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      <AppHeader breadcrumb={breadcrumb} actions={actions} />
      <main className="flex-1 bg-background">{children}</main>
    </div>
  )
}
