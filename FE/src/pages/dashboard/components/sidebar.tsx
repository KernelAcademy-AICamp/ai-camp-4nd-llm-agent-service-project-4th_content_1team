"use client"

import { Link, useLocation } from "react-router-dom"
import { Play, Calendar, FileText, ImageIcon, Upload, Settings, LogOut, User, BarChart3 } from "lucide-react"
import { cn } from "../../../lib/utils"
import { Avatar, AvatarFallback } from "../../../components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../../components/ui/dropdown-menu"

const navItems = [
  { href: "/dashboard", label: "대시보드", icon: Calendar },
  { href: "/analysis", label: "분석", icon: BarChart3 },
  { href: "/script", label: "스크립트", icon: FileText },
  { href: "/thumbnail", label: "썸네일", icon: ImageIcon },
  { href: "/upload", label: "업로드", icon: Upload },
]

export function DashboardSidebar() {
  const { pathname } = useLocation()

  return (
    <aside className="w-64 border-r border-border bg-sidebar p-4 flex flex-col hidden md:flex">
      {/* Logo */}
      <Link to="/dashboard" className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
          <Play className="w-5 h-5 text-primary-foreground fill-current" />
        </div>
        <span className="text-xl font-bold text-sidebar-foreground">CreatorHub</span>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/")
          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition-all",
                isActive
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* User Section */}
      <div className="pt-4 border-t border-sidebar-border">
        <DropdownMenu>
          <DropdownMenuTrigger className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-sidebar-accent/50 transition-colors">
            <Avatar className="w-9 h-9">
              <AvatarFallback className="bg-primary text-primary-foreground text-sm">
                홍
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 text-left">
              <p className="text-sm font-medium text-sidebar-foreground">홍길동</p>
              <p className="text-xs text-muted-foreground">게임 채널</p>
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56">
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              프로필
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              설정
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <Link to="/">
              <DropdownMenuItem className="text-destructive">
                <LogOut className="mr-2 h-4 w-4" />
                로그아웃
              </DropdownMenuItem>
            </Link>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  )
}
