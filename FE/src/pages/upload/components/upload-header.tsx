"use client"

import { useSearchParams } from "react-router-dom"
import { Button } from "../../../components/ui/button"
import { Badge } from "../../../components/ui/badge"
import { ChevronRight, Home, Upload } from "lucide-react"
import { Link } from "react-router-dom"

export function UploadHeader() {
  const [searchParams] = useSearchParams()
  const topic = searchParams.get("topic") || "2026 게임 트렌드 예측"

  return (
    <header className="border-b border-border p-4 flex items-center justify-between bg-card/30 backdrop-blur">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
          <Link to="/dashboard" className="hover:text-primary transition-colors">
            <Home className="w-4 h-4" />
          </Link>
          <ChevronRight className="w-4 h-4" />
          <Link to="/dashboard" className="hover:text-primary transition-colors">
            업로드 목록
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="font-semibold text-foreground">{topic}</span>
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">YouTube 업로드</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="secondary" className="text-xs">
              <Upload className="w-3 h-3 mr-1" />
              {topic}
            </Badge>
          </div>
        </div>
      </div>
    </header>
  )
}
