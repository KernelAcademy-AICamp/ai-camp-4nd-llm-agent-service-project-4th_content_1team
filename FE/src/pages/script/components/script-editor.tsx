"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Button } from "../../../components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../components/ui/tabs"
import { Copy, RefreshCw, Sparkles, Clock, Check, AlignLeft } from "lucide-react"
import type { Citation } from "../../../lib/api/services"

interface ScriptEditorProps {
  apiData?: { hook: string; chapters: { title: string; content: string }[]; outro: string } | null;
  isGenerating?: boolean;
  onRegenerate?: () => void;
  citations?: Citation[];
  onCitationClick?: (sourceUrl: string) => void;
}

export function ScriptEditor({ apiData, isGenerating = false, onRegenerate, citations = [], onCitationClick }: ScriptEditorProps = {}) {
  const [intro, setIntro] = useState("")
  const [body, setBody] = useState("")
  const [outro, setOutro] = useState("")
  const [copied, setCopied] = useState(false)
  const [fullViewOverride, setFullViewOverride] = useState<string | null>(null)

  // API 데이터가 있으면 사용
  useEffect(() => {
    if (apiData) {
      setIntro(apiData.hook || "");
      setBody(apiData.chapters.map(ch => `## ${ch.title}\n\n${ch.content}`).join("\n\n") || "");
      setOutro(apiData.outro || "");
    }
  }, [apiData]);

  // 섹션 편집 시 전체 보기 오버라이드 초기화
  useEffect(() => {
    setFullViewOverride(null)
  }, [intro, body, outro])

  const derivedFull = `${intro}\n\n${body}\n\n${outro}`
  const fullScript = fullViewOverride ?? derivedFull
  const wordCount = fullScript.replace(/\s+/g, " ").split(" ").length
  const estimatedMinutes = Math.ceil(wordCount / 150)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(fullScript)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRegenerate = async () => {
    if (onRegenerate) {
      onRegenerate();
    }
  }

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div>
          <CardTitle className="text-lg">AI 스크립트</CardTitle>
          <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <AlignLeft className="w-4 h-4" />
              <span>{wordCount} 단어</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              <span>약 {estimatedMinutes}분</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRegenerate}
            disabled={isGenerating}
            className="gap-2 bg-transparent"
          >
            <RefreshCw className={`w-4 h-4 ${isGenerating ? "animate-spin" : ""}`} />
            재생성
          </Button>
          <Button variant="outline" size="sm" onClick={handleCopy} className="gap-2 bg-transparent">
            {copied ? (
              <>
                <Check className="w-4 h-4 text-accent" />
                복사됨
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                복사
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto">
        {!intro && !body && !outro ? (
          // Empty State
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-3 p-8">
              <div className="text-4xl">💭</div>
              <p className="text-muted-foreground text-sm">
                "재생성 버튼을 눌러<br />AI 스크립트를 생성하세요"
              </p>
            </div>
          </div>
        ) : (
          // 실제 컨텐츠
          <Tabs defaultValue="full" className="h-full flex flex-col">
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="sections">섹션별 편집</TabsTrigger>
              <TabsTrigger value="full">전체 보기</TabsTrigger>
            </TabsList>

            <TabsContent value="sections" className="flex-1 space-y-4 overflow-auto">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <label className="text-sm font-medium">인트로</label>
                </div>
                <EditableWithCitations
                  value={intro}
                  onChange={setIntro}
                  citations={citations}
                  onCitationClick={onCitationClick}
                  minHeight="150px"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <label className="text-sm font-medium">본문</label>
                </div>
                <EditableWithCitations
                  value={body}
                  onChange={setBody}
                  citations={citations}
                  onCitationClick={onCitationClick}
                  minHeight="300px"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <label className="text-sm font-medium">아웃트로</label>
                </div>
                <EditableWithCitations
                  value={outro}
                  onChange={setOutro}
                  citations={citations}
                  onCitationClick={onCitationClick}
                  minHeight="120px"
                />
              </div>
            </TabsContent>

            <TabsContent value="full" className="flex-1">
              <EditableWithCitations
                value={fullViewOverride ?? derivedFull}
                onChange={setFullViewOverride}
                citations={citations}
                onCitationClick={onCitationClick}
                minHeight="400px"
              />
            </TabsContent>
          </Tabs>
        )}

        {/* 인용 범례 (Citation Legend) */}
        {citations.length > 0 && (
          <div className="mt-4 p-3 rounded-lg bg-muted/20 border border-border/30">
            <p className="text-xs font-semibold text-muted-foreground mb-2">📌 인용 출처</p>
            <div className="space-y-1">
              {citations.map((c) => (
                <div key={c.number} className="flex items-start gap-2 text-xs">
                  <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-primary/20 text-primary text-[9px] font-bold flex-shrink-0 mt-0.5">
                    {c.marker}
                  </span>
                  <span className="text-muted-foreground">
                    <span className="font-medium text-foreground/80">{c.source}</span>
                    {" — "}
                    {c.content?.slice(0, 60)}{c.content && c.content.length > 60 ? "..." : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}


// =============================================================================
// EditableWithCitations - 편집 가능 + ①②③ 클릭 가능한 컴포넌트
// =============================================================================

interface EditableWithCitationsProps {
  value: string;
  onChange: (v: string) => void;
  citations: Citation[];
  onCitationClick?: (sourceUrl: string) => void;
  minHeight?: string;
}

function EditableWithCitations({
  value,
  onChange,
  citations = [],
  onCitationClick,
  minHeight = "150px",
}: EditableWithCitationsProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const isEditing = useRef(false)

  // 텍스트 → HTML 변환 (①②③를 클릭 가능한 뱃지로)
  const buildHtml = useCallback((text: string) => {
    const circlePattern = /([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])/g
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br>")

    html = html.replace(circlePattern, (match) => {
      const c = citations.find(ct => ct.marker === match)
      if (c) {
        const tooltip = `${c.source}: ${(c.content || "").slice(0, 60)}`.replace(/"/g, "&quot;").replace(/'/g, "&#39;")
        return (
          `<span class="cite-badge" data-url="${c.source_url || ""}" title="${tooltip}" contenteditable="false"` +
          ` style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;` +
          `border-radius:50%;background:hsl(var(--primary)/0.2);color:hsl(var(--primary));` +
          `font-size:10px;font-weight:bold;cursor:pointer;margin:0 2px;vertical-align:super;` +
          `transition:background 0.2s;"` +
          ` onmouseover="this.style.background='hsl(var(--primary)/0.4)'"` +
          ` onmouseout="this.style.background='hsl(var(--primary)/0.2)'"` +
          `>${match}</span>`
        )
      }
      return match
    })

    return html
  }, [citations])

  // HTML → 텍스트 추출 (뱃지를 다시 ①②③ 글자로 복원)
  const extractText = useCallback(() => {
    if (!divRef.current) return ""
    const clone = divRef.current.cloneNode(true) as HTMLDivElement

    // <br> → 줄바꿈
    clone.querySelectorAll("br").forEach(br => {
      const newline = document.createTextNode("\n")
      br.parentNode?.replaceChild(newline, br)
    })

    // 뱃지 → 원래 마커 글자
    clone.querySelectorAll(".cite-badge").forEach(badge => {
      const marker = badge.textContent || ""
      badge.replaceWith(marker)
    })

    // div/p 태그 줄바꿈 처리
    clone.querySelectorAll("div, p").forEach(block => {
      block.prepend(document.createTextNode("\n"))
    })

    return (clone.textContent || "").replace(/^\n/, "")
  }, [])

  // props에서 값이 바뀌면 HTML 갱신 (편집 중이 아닐 때만)
  useEffect(() => {
    if (divRef.current && !isEditing.current) {
      divRef.current.innerHTML = buildHtml(value)
    }
  }, [value, buildHtml])

  // 편집 시 텍스트 추출 → state 업데이트
  const handleInput = useCallback(() => {
    isEditing.current = true
    const text = extractText()
    onChange(text)
    requestAnimationFrame(() => {
      isEditing.current = false
    })
  }, [extractText, onChange])

  // ①②③ 뱃지 클릭 → 기사 표시
  const handleClick = useCallback((e: React.MouseEvent) => {
    const target = e.target as HTMLElement
    if (target.classList.contains("cite-badge")) {
      e.preventDefault()
      e.stopPropagation()
      const url = target.getAttribute("data-url")
      if (url && onCitationClick) {
        onCitationClick(url)
      }
    }
  }, [onCitationClick])

  return (
    <div
      ref={divRef}
      contentEditable
      onInput={handleInput}
      onClick={handleClick}
      className="p-3 rounded-md border border-border/50 bg-muted/30 whitespace-pre-wrap outline-none focus:ring-1 focus:ring-primary/50 overflow-auto text-sm"
      style={{ minHeight }}
      suppressContentEditableWarning
    />
  )
}
