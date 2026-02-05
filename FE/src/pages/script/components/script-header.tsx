"use client"

import { useSearchParams } from "react-router-dom"
import { Button } from "../../../components/ui/button"
import { Badge } from "../../../components/ui/badge"
import { ChevronRight, Home, Edit3 } from "lucide-react"
import { Link } from "react-router-dom"

export function ScriptHeader() {
  const [searchParams] = useSearchParams()
  const topic = searchParams.get("topic") || "제목 없음"

  return (
    <header className="border-b border-border p-4 flex items-center justify-between bg-card/30 backdrop-blur">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
          <Link to="/dashboard" className="hover:text-primary transition-colors">
            <Home className="w-4 h-4" />
          </Link>
          <ChevronRight className="w-4 h-4" />
          <Link to="/dashboard" className="hover:text-primary transition-colors">
            스크립트 목록
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="font-semibold text-foreground">{topic}</span>
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">{topic}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="secondary" className="text-xs">
              <Edit3 className="w-3 h-3 mr-1" />
              AI 생성
            </Badge>
            <span className="text-sm text-muted-foreground">마지막 저장: 방금 전</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" className="gap-2 bg-transparent">
          <Edit3 className="w-4 h-4" />
          저장
        </Button>
        <Link to={`/thumbnail?topic=${encodeURIComponent(topic)}`}>
          <Button className="gap-2 bg-primary hover:bg-primary/90">
            <Edit3 className="w-4 h-4" />
            썸네일 생성
          </Button>
        </Link>
      </div>
    </header>
  )
}
