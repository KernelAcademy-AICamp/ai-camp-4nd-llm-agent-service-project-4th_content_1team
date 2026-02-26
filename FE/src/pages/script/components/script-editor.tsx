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

/**
 * 전체 보기 텍스트를 ## 마커 기준으로 intro/body/outro로 분리
 * - intro: 첫 번째 ## 이전
 * - body: ## 챕터들 (마지막 챕터의 내용 1블록 포함)
 * - outro: 마지막 챕터 이후 나머지
 */
function parseFullScript(text: string): { intro: string; body: string; outro: string } {
  const blocks = text.split('\n\n')
  const firstIdx = blocks.findIndex(b => b.startsWith('## '))

  if (firstIdx === -1) {
    return { intro: text, body: '', outro: '' }
  }

  const parsedIntro = blocks.slice(0, firstIdx).join('\n\n')

  // 마지막 ## 블록 찾기
  let lastIdx = firstIdx
  for (let i = blocks.length - 1; i >= firstIdx; i--) {
    if (blocks[i].startsWith('## ')) {
      lastIdx = i
      break
    }
  }

  // 마지막 ## 헤더 + 내용 1블록까지 = body
  const bodyEnd = Math.min(lastIdx + 2, blocks.length)
  const parsedBody = blocks.slice(firstIdx, bodyEnd).join('\n\n')
  const parsedOutro = blocks.slice(bodyEnd).join('\n\n')

  return { intro: parsedIntro, body: parsedBody, outro: parsedOutro }
}

export function ScriptEditor({ apiData, isGenerating = false, onRegenerate, citations = [], onCitationClick }: ScriptEditorProps = {}) {
  const [intro, setIntro] = useState("")
  const [body, setBody] = useState("")
  const [outro, setOutro] = useState("")
  const [copied, setCopied] = useState(false)
  const [fullViewOverride, setFullViewOverride] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("full")

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

  // 탭 전환 시 전체 보기 → 섹션별 편집 동기화
  const handleTabChange = useCallback((value: string) => {
    if (value === "sections" && fullViewOverride !== null) {
      const parsed = parseFullScript(fullViewOverride)
      setIntro(parsed.intro)
      setBody(parsed.body)
      setOutro(parsed.outro)
      setFullViewOverride(null)
    }
    setActiveTab(value)
  }, [fullViewOverride])

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
          <Tabs value={activeTab} onValueChange={handleTabChange} className="h-full flex flex-col">
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
                  <span className="inline-flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold flex-shrink-0 mt-0.5" style={{ background: 'rgba(251,191,36,0.25)', color: '#F59E0B' }}>
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

  // 뱃지 HTML 생성 헬퍼
  const makeBadge = useCallback((marker: string) => {
    const c = citations.find(ct => ct.marker === marker)
    if (!c) return marker
    const tooltip = `${c.source}: ${(c.content || "").slice(0, 60)}`.replace(/"/g, "&quot;").replace(/'/g, "&#39;")
    return (
      `<span class="cite-badge" data-url="${c.source_url || ""}" title="${tooltip}" contenteditable="false"` +
      ` style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;` +
      `border-radius:50%;background:rgba(251,191,36,0.25);color:#F59E0B;` +
      `font-size:10px;font-weight:bold;cursor:pointer;margin:0 2px;vertical-align:super;` +
      `transition:background 0.2s;"` +
      ` onmouseover="this.style.background='rgba(251,191,36,0.45)'"` +
      ` onmouseout="this.style.background='rgba(251,191,36,0.25)'"` +
      `>${marker}</span>`
    )
  }, [citations])

  // 텍스트 → HTML 변환 (인용 문장 하이라이트 + ①②③ 뱃지)
  const buildHtml = useCallback((text: string) => {
    // HTML 이스케이프
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")

    // 마커 기준으로 텍스트 분할 (마커를 캡처 그룹으로 유지)
    const parts = html.split(/([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]+\.?)/g)
    // parts = [텍스트, 마커들, 텍스트, 마커들, ...]

    // 인용 문장 시작 위치 찾기 (숫자.숫자 패턴은 문장 경계로 무시)
    const findCitedStart = (s: string): number => {
      // 모든 문장 경계 위치 수집
      const breaks: number[] = []
      for (let i = 0; i < s.length; i++) {
        const ch = s[i]
        if (ch === '\n') {
          breaks.push(i)
        } else if (ch === '?' || ch === '!' || ch === '。') {
          breaks.push(i)
        } else if (ch === '.') {
          const prevIsDigit = i > 0 && /\d/.test(s[i - 1])
          const nextIsDigit = i < s.length - 1 && /\d/.test(s[i + 1])
          if (!(prevIsDigit && nextIsDigit)) {
            breaks.push(i)
          }
        }
      }

      if (breaks.length === 0) return 0 // 경계 없으면 전체가 인용

      const lastBreak = breaks[breaks.length - 1]
      const textAfterLast = s.slice(lastBreak + 1).trim()

      if (textAfterLast.length === 0) {
        // 마지막 경계가 텍스트 끝에 있음 (예: "않나요?" + 마커)
        // → 그 전 경계부터 하이라이트
        if (breaks.length >= 2) {
          return breaks[breaks.length - 2] + 1
        }
        return 0 // 경계가 하나뿐이면 전체가 인용
      }

      // 마지막 경계 이후에 텍스트가 있으면 거기부터 하이라이트
      return lastBreak + 1
    }

    let result = ''
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isMarker = /^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]+\.?$/.test(part)

      if (isMarker) {
        // 마커를 뱃지로 변환
        const badges = part.replace(/[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]/g, (m: string) => makeBadge(m))
        result += badges
      } else {
        // 다음 파트가 마커인지 확인
        const nextIsMarker = i + 1 < parts.length && /^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]+\.?$/.test(parts[i + 1])

        if (nextIsMarker && part.trim().length > 0) {
          // 이 텍스트 뒤에 마커가 온다 → 인용 문장 시작 위치를 찾아서 그 이후만 하이라이트
          const citedStart = findCitedStart(part)

          if (citedStart > 0) {
            // 인용 시작 이전 = 일반 텍스트
            const before = part.slice(0, citedStart)
            // 인용 시작 이후 = 인용 문장 (하이라이트)
            const cited = part.slice(citedStart)
            result += before
            result += (
              `<span class="cite-highlight"` +
              ` style="background:rgba(251,191,36,0.10);border-left:3px solid rgba(251,191,36,0.5);` +
              `padding:1px 4px;border-radius:0 3px 3px 0;"` +
              `>${cited}</span>`
            )
          } else {
            // 전체가 인용 문장
            result += (
              `<span class="cite-highlight"` +
              ` style="background:rgba(251,191,36,0.10);border-left:3px solid rgba(251,191,36,0.5);` +
              `padding:1px 4px;border-radius:0 3px 3px 0;"` +
              `>${part}</span>`
            )
          }
        } else {
          // 마커가 뒤에 안 오면 일반 텍스트
          result += part
        }
      }
    }

    result = result.replace(/\n/g, "<br>")
    return result
  }, [citations, makeBadge])

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

    // 인용 하이라이트 → 내부 텍스트만 유지
    clone.querySelectorAll(".cite-highlight").forEach(hl => {
      const inner = hl.textContent || ""
      hl.replaceWith(inner)
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
