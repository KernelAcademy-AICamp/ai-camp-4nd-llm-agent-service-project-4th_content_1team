"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Button } from "../../../components/ui/button"
import { Textarea } from "../../../components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../components/ui/tabs"
import { Copy, RefreshCw, Sparkles, Clock, Check, AlignLeft } from "lucide-react"

interface ScriptEditorProps {
  apiData?: { hook: string; chapters: { title: string; content: string }[]; outro: string } | null;
  isGenerating?: boolean;
  onRegenerate?: () => void;
}

export function ScriptEditor({ apiData, isGenerating = false, onRegenerate }: ScriptEditorProps = {}) {
  const [intro, setIntro] = useState("")
  const [body, setBody] = useState("")
  const [outro, setOutro] = useState("")
  const [copied, setCopied] = useState(false)

  // API 데이터가 있으면 사용
  useEffect(() => {
    if (apiData) {
      setIntro(apiData.hook || "");
      setBody(apiData.chapters.map(ch => `## ${ch.title}\n\n${ch.content}`).join("\n\n") || "");
      setOutro(apiData.outro || "");
    }
  }, [apiData]);

  const fullScript = `${intro}\n\n${body}\n\n${outro}`
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
          <Tabs defaultValue="sections" className="h-full flex flex-col">
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
                <Textarea
                  value={intro}
                  onChange={(e) => setIntro(e.target.value)}
                  className="min-h-[150px] resize-none bg-muted/30"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <label className="text-sm font-medium">본문</label>
                </div>
                <Textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="min-h-[300px] resize-none bg-muted/30"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <label className="text-sm font-medium">아웃트로</label>
                </div>
                <Textarea
                  value={outro}
                  onChange={(e) => setOutro(e.target.value)}
                  className="min-h-[120px] resize-none bg-muted/30"
                />
              </div>
            </TabsContent>

            <TabsContent value="full" className="flex-1">
              <div className="prose prose-invert prose-sm max-w-none p-4 rounded-lg bg-muted/30 whitespace-pre-wrap">
                {fullScript}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  )
}
