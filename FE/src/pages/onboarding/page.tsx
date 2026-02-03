"use client"

import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "../../components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card"
import { Input } from "../../components/ui/input"
import { Label } from "../../components/ui/label"
import { RadioGroup, RadioGroupItem } from "../../components/ui/radio-group"
import { Slider } from "../../components/ui/slider"
import { Play, ChevronRight, ChevronLeft, Check, Gamepad2, BookOpen, Utensils, Dumbbell, Palette, Music, Camera, Briefcase, Tv, Loader2 } from "lucide-react"
import { Link } from "react-router-dom"
import { generatePersona, updatePersona } from "../../lib/api"
import type { PersonaResponse } from "../../lib/api/types"

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
  const navigate = useNavigate()

  // 기존 상태 (Step 2, 3용 - 나중에 활용 가능)
  const [step, setStep] = useState(1)
  const [channelName, setChannelName] = useState("")
  const [uploadFrequency, setUploadFrequency] = useState([2])
  const [targetAudience, setTargetAudience] = useState("")

  // 새로운 상태 (페르소나 연동)
  const [isAnalyzing, setIsAnalyzing] = useState(true)
  const [persona, setPersona] = useState<PersonaResponse | null>(null)
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const totalSteps = 1  // 현재는 1단계만 사용

  // StrictMode 중복 호출 방지
  const hasCalledRef = useRef(false)

  // 페이지 진입 시 페르소나 생성
  useEffect(() => {
    if (hasCalledRef.current) return  // 이미 호출했으면 스킵
    hasCalledRef.current = true

    const analyzeChannel = async () => {
      try {
        setIsAnalyzing(true)
        setError(null)

        const response = await generatePersona()

        if (response.success && response.persona) {
          setPersona(response.persona)
        } else {
          setError(response.message || "채널 분석에 실패했습니다.")
        }
      } catch (err: any) {
        console.error("페르소나 생성 실패:", err)
        setError(err.response?.data?.detail || "채널 분석 중 오류가 발생했습니다.")
      } finally {
        setIsAnalyzing(false)
      }
    }

    analyzeChannel()
  }, [])

  // 카테고리 복수 선택 토글
  const toggleCategory = (categoryId: string) => {
    setSelectedCategories(prev =>
      prev.includes(categoryId)
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    )
  }

  // 시작하기 클릭 (선호 카테고리 저장 후 대시보드 이동)
  const handleStart = async () => {
    try {
      setIsSaving(true)

      if (selectedCategories.length > 0) {
        await updatePersona({
          preferred_categories: selectedCategories
        })
      }

      navigate('/dashboard')
    } catch (err: any) {
      console.error("카테고리 저장 실패:", err)
      navigate('/dashboard')  // 실패해도 대시보드로 이동
    } finally {
      setIsSaving(false)
    }
  }

  // 분석된 카테고리 텍스트
  const getAnalyzedCategoryText = () => {
    if (!persona?.analyzed_categories || persona.analyzed_categories.length === 0) {
      return "분석된 카테고리 없음"
    }
    return persona.analyzed_categories.join(", ")
  }

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
                <CardTitle className="text-2xl">
                  {isAnalyzing ? "채널을 분석하고 있어요" : error ? "분석 중 문제가 발생했어요" : "안녕하세요!"}
                </CardTitle>
                <CardDescription>
                  {isAnalyzing
                    ? "잠시만 기다려 주세요..."
                    : error
                    ? error
                    : "최적의 맞춤 서비스를 위해 몇 가지만 더 확인할게요"}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* 로딩 상태 */}
                {isAnalyzing && (
                  <div className="flex flex-col items-center justify-center py-12">
                    <Loader2 className="w-16 h-16 text-primary animate-spin mb-6" />
                    <p className="text-muted-foreground text-center">
                      채널의 영상 데이터를 분석하여<br />
                      맞춤형 콘텐츠를 추천해 드릴게요
                    </p>
                  </div>
                )}

                {/* 에러 상태 */}
                {!isAnalyzing && error && (
                  <div className="flex flex-col items-center justify-center py-8">
                    <Button
                      onClick={() => window.location.reload()}
                      className="bg-primary hover:bg-primary/90"
                    >
                      다시 시도하기
                    </Button>
                  </div>
                )}

                {/* 분석 완료 상태 */}
                {!isAnalyzing && !error && (
                  <>
                    {/* 분석 결과 표시 (채널 이름 입력 대신) */}
                    <div className="p-4 rounded-xl bg-primary/10 border border-primary/20">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                          <Check className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-semibold text-foreground">분석 결과</p>
                          <p className="text-sm text-muted-foreground mt-1">
                            현재 채널의 카테고리는 <span className="text-primary font-medium">{getAnalyzedCategoryText()}</span> 입니다.
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* 선호 카테고리 선택 (복수 선택) */}
                    <div className="space-y-4">
                      <Label>선호 카테고리 <span className="text-muted-foreground font-normal">(복수 선택 가능)</span></Label>
                      <p className="text-sm text-muted-foreground">원하는 카테고리가 있다면 선택해 주세요.</p>
                      <div className="grid grid-cols-3 gap-3">
                        {categories.map((category) => {
                          const Icon = category.icon
                          const isSelected = selectedCategories.includes(category.id)
                          return (
                            <button
                              key={category.id}
                              onClick={() => toggleCategory(category.id)}
                              className={`p-4 rounded-xl border transition-all flex flex-col items-center gap-2 ${isSelected
                                ? "border-primary bg-primary/10"
                                : "border-border/50 hover:border-primary/50 hover:bg-muted/50"
                                }`}
                            >
                              <Icon className={`w-6 h-6 ${isSelected ? "text-primary" : "text-muted-foreground"}`} />
                              <span className={`text-sm font-medium ${isSelected ? "text-primary" : "text-foreground"}`}>
                                {category.label}
                              </span>
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  </>
                )}
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

          {/* 하단 버튼 - 분석 완료 후에만 표시 */}
          {!isAnalyzing && !error && (
            <div className="p-6 pt-0 flex justify-end">
              <Button
                onClick={handleStart}
                disabled={isSaving}
                className="gap-2 bg-primary hover:bg-primary/90"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    저장 중...
                  </>
                ) : (
                  <>
                    시작하기
                    <Check className="w-4 h-4" />
                  </>
                )}
              </Button>
            </div>
          )}
        </Card>
      </main>
    </div>
  )
}
