"use client"

import { useState } from "react"
import { Button } from "../../components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card"
import { Input } from "../../components/ui/input"
import { Label } from "../../components/ui/label"
import { RadioGroup, RadioGroupItem } from "../../components/ui/radio-group"
import { Slider } from "../../components/ui/slider"
import { Play, ChevronRight, ChevronLeft, Check, Gamepad2, BookOpen, Utensils, Dumbbell, Palette, Music, Camera, Briefcase, Tv } from "lucide-react"
import { Link } from "react-router-dom"

const categories = [
  { id: "gaming", label: "게임", icon: Gamepad2 },
  { id: "education", label: "교육/정보", icon: BookOpen },
  { id: "food", label: "먹방/요리", icon: Utensils },
  { id: "fitness", label: "운동/건강", icon: Dumbbell },
  { id: "art", label: "예술/창작", icon: Palette },
  { id: "music", label: "음악", icon: Music },
  { id: "vlog", label: "브이로그", icon: Camera },
  { id: "business", label: "비즈니스", icon: Briefcase },
  { id: "entertainment", label: "엔터테인먼트", icon: Tv },
]

export default function OnboardingPage() {
  const [step, setStep] = useState(1)
  const [channelName, setChannelName] = useState("")
  const [selectedCategory, setSelectedCategory] = useState("")
  const [uploadFrequency, setUploadFrequency] = useState([2])
  const [targetAudience, setTargetAudience] = useState("")

  const totalSteps = 3

  const handleNext = () => {
    if (step < totalSteps) {
      setStep(step + 1)
    }
  }

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
            <Play className="w-5 h-5 text-primary-foreground fill-current" />
          </div>
          <span className="text-xl font-bold text-foreground">CreatorHub</span>
        </div>
        <div className="flex items-center gap-2">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={`h-2 rounded-full transition-all ${i + 1 === step ? "w-8 bg-primary" : i + 1 < step ? "w-2 bg-primary" : "w-2 bg-muted"
                }`}
            />
          ))}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-6">
        <Card className="w-full max-w-2xl border-border/50 bg-card/50 backdrop-blur">
          {step === 1 && (
            <>
              <CardHeader className="text-center">
                <CardTitle className="text-2xl">채널 정보를 알려주세요</CardTitle>
                <CardDescription>
                  맞춤형 콘텐츠 추천을 위해 채널 정보가 필요해요
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="channel-name">채널 이름</Label>
                  <Input
                    id="channel-name"
                    placeholder="내 채널 이름"
                    value={channelName}
                    onChange={(e) => setChannelName(e.target.value)}
                    className="h-12"
                  />
                </div>

                <div className="space-y-4">
                  <Label>채널 카테고리</Label>
                  <div className="grid grid-cols-3 gap-3">
                    {categories.map((category) => {
                      const Icon = category.icon
                      return (
                        <button
                          key={category.id}
                          onClick={() => setSelectedCategory(category.id)}
                          className={`p-4 rounded-xl border transition-all flex flex-col items-center gap-2 ${selectedCategory === category.id
                            ? "border-primary bg-primary/10"
                            : "border-border/50 hover:border-primary/50 hover:bg-muted/50"
                            }`}
                        >
                          <Icon className={`w-6 h-6 ${selectedCategory === category.id ? "text-primary" : "text-muted-foreground"}`} />
                          <span className={`text-sm font-medium ${selectedCategory === category.id ? "text-primary" : "text-foreground"}`}>
                            {category.label}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              </CardContent>
            </>
          )}

          {step === 2 && (
            <>
              <CardHeader className="text-center">
                <CardTitle className="text-2xl">업로드 주기를 설정하세요</CardTitle>
                <CardDescription>
                  주간 업로드 횟수에 맞춰 콘텐츠를 추천해드려요
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                <div className="space-y-6">
                  <div className="text-center">
                    <span className="text-6xl font-bold text-primary">{uploadFrequency[0]}</span>
                    <span className="text-2xl text-muted-foreground ml-2">회 / 주</span>
                  </div>
                  <Slider
                    value={uploadFrequency}
                    onValueChange={setUploadFrequency}
                    max={7}
                    min={1}
                    step={1}
                    className="w-full"
                  />
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>1회</span>
                    <span>7회 (매일)</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-muted/50 border border-border/50">
                  <p className="text-sm text-muted-foreground text-center">
                    주 {uploadFrequency[0]}회 업로드 시, 월 평균 <span className="text-primary font-semibold">{uploadFrequency[0] * 4}개</span>의 콘텐츠 주제를 추천받을 수 있어요.
                  </p>
                </div>
              </CardContent>
            </>
          )}

          {step === 3 && (
            <>
              <CardHeader className="text-center">
                <CardTitle className="text-2xl">타겟 시청자층을 선택하세요</CardTitle>
                <CardDescription>
                  시청자에 맞는 콘텐츠 스타일을 추천해드려요
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <RadioGroup value={targetAudience} onValueChange={setTargetAudience} className="space-y-3">
                  <div className={`flex items-center space-x-3 p-4 rounded-xl border cursor-pointer transition-all ${targetAudience === "teens" ? "border-primary bg-primary/10" : "border-border/50 hover:border-primary/50"
                    }`}>
                    <RadioGroupItem value="teens" id="teens" />
                    <Label htmlFor="teens" className="flex-1 cursor-pointer">
                      <div className="font-medium">10대</div>
                      <div className="text-sm text-muted-foreground">트렌디하고 빠른 콘텐츠</div>
                    </Label>
                  </div>
                  <div className={`flex items-center space-x-3 p-4 rounded-xl border cursor-pointer transition-all ${targetAudience === "20s" ? "border-primary bg-primary/10" : "border-border/50 hover:border-primary/50"
                    }`}>
                    <RadioGroupItem value="20s" id="20s" />
                    <Label htmlFor="20s" className="flex-1 cursor-pointer">
                      <div className="font-medium">20대</div>
                      <div className="text-sm text-muted-foreground">실용적이고 공감가는 콘텐츠</div>
                    </Label>
                  </div>
                  <div className={`flex items-center space-x-3 p-4 rounded-xl border cursor-pointer transition-all ${targetAudience === "30s" ? "border-primary bg-primary/10" : "border-border/50 hover:border-primary/50"
                    }`}>
                    <RadioGroupItem value="30s" id="30s" />
                    <Label htmlFor="30s" className="flex-1 cursor-pointer">
                      <div className="font-medium">30대 이상</div>
                      <div className="text-sm text-muted-foreground">심도 있고 전문적인 콘텐츠</div>
                    </Label>
                  </div>
                  <div className={`flex items-center space-x-3 p-4 rounded-xl border cursor-pointer transition-all ${targetAudience === "all" ? "border-primary bg-primary/10" : "border-border/50 hover:border-primary/50"
                    }`}>
                    <RadioGroupItem value="all" id="all" />
                    <Label htmlFor="all" className="flex-1 cursor-pointer">
                      <div className="font-medium">전 연령대</div>
                      <div className="text-sm text-muted-foreground">누구나 즐길 수 있는 콘텐츠</div>
                    </Label>
                  </div>
                </RadioGroup>
              </CardContent>
            </>
          )}

          <div className="p-6 pt-0 flex justify-between">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={step === 1}
              className="gap-2 bg-transparent"
            >
              <ChevronLeft className="w-4 h-4" />
              이전
            </Button>
            {step < totalSteps ? (
              <Button onClick={handleNext} className="gap-2 bg-primary hover:bg-primary/90">
                다음
                <ChevronRight className="w-4 h-4" />
              </Button>
            ) : (
              <Link to="/dashboard">
                <Button className="gap-2 bg-primary hover:bg-primary/90">
                  시작하기
                  <Check className="w-4 h-4" />
                </Button>
              </Link>
            )}
          </div>
        </Card>
      </main>
    </div>
  )
}
