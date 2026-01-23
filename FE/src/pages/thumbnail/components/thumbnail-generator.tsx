"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Button } from "../../../components/ui/button"
import { Badge } from "../../../components/ui/badge"
import { Input } from "../../../components/ui/input"
import { Label } from "../../../components/ui/label"
import { RadioGroup, RadioGroupItem } from "../../../components/ui/radio-group"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../components/ui/tabs"
import {
  Wand2,
  Download,
  Copy,
  RefreshCw,
  Layout,
  Type,
  Image as ImageIcon,
  Palette,
  MousePointer2,
  Sparkles,
  Zap,
  Target,
  Flame,
  Star,
  Check,
  ShieldAlert,
  Trophy,
  Lock,
  Hash,
  BadgeCheck
} from "lucide-react"

const thumbnailVariants = [
  {
    id: 1,
    title: "강렬한 임팩트",
    concept: "impact",
    headline: "2026년 게임 트렌드",
    subline: "AI가 바꾸는 게임의 미래",
    style: "bg-gradient-to-br from-primary via-chart-1 to-chart-5",
    textColor: "text-white",
    icon: Zap,
    recommended: true
  },
  {
    id: 2,
    title: "미니멀 클린",
    concept: "minimal",
    headline: "게임 트렌드 예측",
    subline: "2026 완벽 가이드",
    style: "bg-gradient-to-br from-background to-muted",
    textColor: "text-foreground",
    icon: Target,
    recommended: false
  },
  {
    id: 3,
    title: "핫 트렌드",
    concept: "hot",
    headline: "꼭 알아야 할",
    subline: "2026 게임 트렌드 TOP 5",
    style: "bg-gradient-to-br from-chart-3 via-destructive to-chart-5",
    textColor: "text-white",
    icon: Flame,
    recommended: false
  },
  {
    id: 4,
    title: "프리미엄 골드",
    concept: "premium",
    headline: "2026 게임 산업",
    subline: "전문가 분석 리포트",
    style: "bg-gradient-to-br from-chart-3 via-chart-4 to-chart-5",
    textColor: "text-background",
    icon: Star,
    recommended: false
  },
]

// 카테고리별 AI 추천 문구
const headlineCategories = [
  {
    id: "avoidance",
    name: "회피형",
    icon: ShieldAlert,
    description: "손실/위험 회피 심리 자극",
    suggestions: [
      { headline: "이거 모르면 큰일납니다", subline: "2026 게임 트렌드 필수 체크" },
      { headline: "아직도 이렇게 하세요?", subline: "게임 유튜버가 반드시 피해야 할 실수" },
      { headline: "이 실수 하나로 망했습니다", subline: "절대 따라하지 마세요" },
      { headline: "지금 안 보면 후회합니다", subline: "놓치면 안 되는 2026 트렌드" },
    ]
  },
  {
    id: "result",
    name: "결과형",
    icon: Trophy,
    description: "성과/결과 중심 어필",
    suggestions: [
      { headline: "조회수 300% 상승한 비결", subline: "이 방법 하나로 채널이 달라졌습니다" },
      { headline: "구독자 10만 달성 노하우", subline: "6개월 만에 가능했던 이유" },
      { headline: "이렇게 하니 수익이 5배", subline: "게임 채널 성장 공식 공개" },
      { headline: "드디어 찾았습니다", subline: "2026년 확실한 성공 전략" },
    ]
  },
  {
    id: "secret",
    name: "비밀폭로형",
    icon: Lock,
    description: "독점 정보/내부자 시점",
    suggestions: [
      { headline: "아무도 안 알려주는 진실", subline: "게임 업계 관계자가 직접 공개" },
      { headline: "업계에서 쉬쉬하는 이야기", subline: "처음으로 공개합니다" },
      { headline: "대기업이 숨기고 싶은 비밀", subline: "이제 다 알려드립니다" },
      { headline: "유출된 내부 문서 분석", subline: "2026년 게임 업계 로드맵" },
    ]
  },
  {
    id: "number",
    name: "숫자형",
    icon: Hash,
    description: "구체적 숫자로 신뢰감 상승",
    suggestions: [
      { headline: "TOP 7 게임 트렌드", subline: "2026년 반드시 알아야 할" },
      { headline: "단 3가지만 기억하세요", subline: "게임 채널 성공 공식" },
      { headline: "5분 만에 정리하는", subline: "2026 게임 업계 핵심 이슈" },
      { headline: "1000만 유튜버의 10가지 습관", subline: "성공하는 크리에이터의 비밀" },
    ]
  },
  {
    id: "verify",
    name: "검증형",
    icon: BadgeCheck,
    description: "팩트체크/실험 결과 공유",
    suggestions: [
      { headline: "직접 해봤습니다", subline: "소문의 진실을 파헤치다" },
      { headline: "팩트체크 완료", subline: "진짜인지 가짜인지 검증해봤습니다" },
      { headline: "100시간 플레이 후 결론", subline: "솔직한 리뷰 공개" },
      { headline: "전문가가 검증한 결과", subline: "데이터로 증명합니다" },
    ]
  },
]

export function ThumbnailGenerator() {
  const [selectedThumbnail, setSelectedThumbnail] = useState(1)
  const [customHeadline, setCustomHeadline] = useState("")
  const [customSubline, setCustomSubline] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState("avoidance")

  const handleRegenerate = () => {
    setIsGenerating(true)
    setTimeout(() => setIsGenerating(false), 1500)
  }

  const handleSuggestionClick = (headline: string, subline: string) => {
    setCustomHeadline(headline)
    setCustomSubline(subline)
  }

  const selectedVariant = thumbnailVariants.find(v => v.id === selectedThumbnail)

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Thumbnail Preview Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Main Preview */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              선택된 썸네일
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedVariant && (
              <div className="space-y-4">
                <div
                  className={`aspect-video rounded-xl ${selectedVariant.style} p-6 flex flex-col justify-center items-center text-center relative overflow-hidden`}
                >
                  {/* Background decoration */}
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.1),transparent_50%)]" />
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_70%,rgba(0,0,0,0.2),transparent_50%)]" />

                  <div className="relative z-10 space-y-2">
                    <h2 className={`text-3xl font-bold ${selectedVariant.textColor} drop-shadow-lg`}>
                      {customHeadline || selectedVariant.headline}
                    </h2>
                    <p className={`text-lg ${selectedVariant.textColor}/80`}>
                      {customSubline || selectedVariant.subline}
                    </p>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="flex-1 gap-2 bg-transparent"
                    onClick={handleRegenerate}
                    disabled={isGenerating}
                  >
                    <RefreshCw className={`w-4 h-4 ${isGenerating ? "animate-spin" : ""}`} />
                    재생성
                  </Button>
                  <Button className="flex-1 gap-2 bg-primary hover:bg-primary/90">
                    <Download className="w-4 h-4" />
                    다운로드
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Customization */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">문구 수정</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="headline">메인 문구</Label>
              <Input
                id="headline"
                placeholder={selectedVariant?.headline}
                value={customHeadline}
                onChange={(e) => setCustomHeadline(e.target.value)}
                className="h-12"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="subline">서브 문구</Label>
              <Input
                id="subline"
                placeholder={selectedVariant?.subline}
                value={customSubline}
                onChange={(e) => setCustomSubline(e.target.value)}
                className="h-12"
              />
            </div>

            {/* AI 추천 문구 - 카테고리별 */}
            <div className="pt-4 border-t border-border/50">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-primary" />
                <p className="text-sm font-medium">AI 추천 문구</p>
              </div>

              <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
                <TabsList className="grid grid-cols-5 h-auto p-1 bg-muted/50">
                  {headlineCategories.map((category) => {
                    const Icon = category.icon
                    return (
                      <TabsTrigger
                        key={category.id}
                        value={category.id}
                        className="flex flex-col gap-1 py-2 px-1 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                      >
                        <Icon className="w-4 h-4" />
                        <span>{category.name}</span>
                      </TabsTrigger>
                    )
                  })}
                </TabsList>

                {headlineCategories.map((category) => (
                  <TabsContent key={category.id} value={category.id} className="mt-3 space-y-2">
                    <p className="text-xs text-muted-foreground mb-2">{category.description}</p>
                    {category.suggestions.map((suggestion, idx) => (
                      <Button
                        key={idx}
                        variant="outline"
                        size="sm"
                        className="w-full justify-start text-left h-auto py-2.5 px-3 bg-transparent hover:bg-primary/10 hover:border-primary/50"
                        onClick={() => handleSuggestionClick(suggestion.headline, suggestion.subline)}
                      >
                        <div className="flex flex-col items-start gap-0.5">
                          <span className="font-medium text-foreground">{suggestion.headline}</span>
                          <span className="text-xs text-muted-foreground">{suggestion.subline}</span>
                        </div>
                      </Button>
                    ))}
                  </TabsContent>
                ))}
              </Tabs>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Variant Selection */}
      <Card className="border-border/50 bg-card/50 backdrop-blur">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg">스타일 선택</CardTitle>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={String(selectedThumbnail)}
            onValueChange={(v) => setSelectedThumbnail(Number(v))}
            className="grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            {thumbnailVariants.map((variant) => {
              const Icon = variant.icon
              const isSelected = selectedThumbnail === variant.id
              return (
                <div key={variant.id} className="relative">
                  <RadioGroupItem
                    value={String(variant.id)}
                    id={`variant-${variant.id}`}
                    className="sr-only"
                  />
                  <Label
                    htmlFor={`variant-${variant.id}`}
                    className={`block cursor-pointer rounded-xl border-2 transition-all overflow-hidden ${isSelected
                      ? "border-primary ring-2 ring-primary/20"
                      : "border-border/50 hover:border-primary/50"
                      }`}
                  >
                    <div className={`aspect-video ${variant.style} p-3 flex flex-col justify-center items-center text-center relative`}>
                      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.1),transparent_50%)]" />
                      <h3 className={`text-sm font-bold ${variant.textColor} relative z-10`}>
                        {variant.headline}
                      </h3>
                      <p className={`text-xs ${variant.textColor}/70 relative z-10`}>
                        {variant.subline}
                      </p>
                    </div>
                    <div className="p-3 bg-card">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Icon className="w-4 h-4 text-muted-foreground" />
                          <span className="text-sm font-medium">{variant.title}</span>
                        </div>
                        {isSelected && (
                          <Check className="w-4 h-4 text-primary" />
                        )}
                      </div>
                    </div>
                  </Label>
                  {variant.recommended && (
                    <Badge className="absolute -top-2 -right-2 bg-primary text-primary-foreground text-xs">
                      추천
                    </Badge>
                  )}
                </div>
              )
            })}
          </RadioGroup>
        </CardContent>
      </Card>
    </div>
  )
}
