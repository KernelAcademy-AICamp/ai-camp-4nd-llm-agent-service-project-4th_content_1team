"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Button } from "../../../components/ui/button"
import { Textarea } from "../../../components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../components/ui/tabs"
import { Wand2, Save, History, Copy, RefreshCw, FileText, Sparkles, Clock, Check, AlignLeft } from "lucide-react"
import { useSearchParams } from "react-router-dom"

const sampleScripts: Record<string, { intro: string; body: string; outro: string }> = {
  "2026 게임 트렌드 예측": {
    intro: `안녕하세요, 여러분! 오늘은 2026년 게임 업계를 뒤흔들 트렌드에 대해 이야기해볼 건데요.

지난 한 해 동안 게임 산업은 정말 많은 변화를 겪었습니다. AI 기술의 발전, 클라우드 게이밍의 성장, 그리고 메타버스의 진화까지... 과연 올해는 어떤 트렌드가 우리를 기다리고 있을까요?`,
    body: `첫 번째로 주목해야 할 트렌드는 바로 'AI 생성 콘텐츠'입니다.

이제 게임 개발사들은 AI를 활용해 NPC의 대화, 퀘스트 생성, 심지어 맵 디자인까지 자동화하고 있습니다. 특히 프로시저럴 생성 기술과 결합된 AI는 플레이어마다 완전히 다른 게임 경험을 제공할 수 있게 되었죠.

두 번째 트렌드는 '하이브리드 게이밍'입니다.

PC, 콘솔, 모바일의 경계가 완전히 무너지고 있습니다. 하나의 계정으로 어떤 기기에서든 이어서 플레이하고, 크로스플레이는 이제 기본 기능이 되었습니다.

세 번째는 '소셜 게이밍 2.0'입니다.

단순히 친구와 함께 게임하는 것을 넘어, 게임 안에서 콘서트를 보고, 쇼핑을 하고, 새로운 사람들을 만나는 '메타버스형 소셜 플랫폼'으로 진화하고 있습니다.`,
    outro: `자, 오늘 소개해드린 2026년 게임 트렌드 어떠셨나요?

여러분은 어떤 트렌드가 가장 기대되시나요? 댓글로 의견 남겨주시고, 이런 게임 트렌드 소식이 궁금하시다면 구독과 좋아요 부탁드립니다!

다음 영상에서 뵙겠습니다. 감사합니다!`
  }
}

export function ScriptEditor() {
  const searchParams = useSearchParams()
  // const topic = searchParams.get("topic") || "2026 게임 트렌드 예측"
  const defaultScript = sampleScripts["2026 게임 트렌드 예측"]

  const [intro, setIntro] = useState(defaultScript.intro)
  const [body, setBody] = useState(defaultScript.body)
  const [outro, setOutro] = useState(defaultScript.outro)
  const [copied, setCopied] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)

  const fullScript = `${intro}\n\n${body}\n\n${outro}`
  const wordCount = fullScript.replace(/\s+/g, " ").split(" ").length
  const estimatedMinutes = Math.ceil(wordCount / 150)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(fullScript)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRegenerate = async () => {
    setIsRegenerating(true)
    // Simulate AI regeneration
    setTimeout(() => {
      setIsRegenerating(false)
    }, 1500)
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
            disabled={isRegenerating}
            className="gap-2 bg-transparent"
          >
            <RefreshCw className={`w-4 h-4 ${isRegenerating ? "animate-spin" : ""}`} />
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
      </CardContent>
    </Card>
  )
}
