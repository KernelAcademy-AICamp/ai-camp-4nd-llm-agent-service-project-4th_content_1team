"use client"

import { useState, useMemo } from "react"
import { Button } from "../../../components/ui/button"
import { Check } from "lucide-react"
import { cn } from "../../../lib/utils"

/* 스펙 § Step 4: 선택한 카테고리 기반 주제/분위기 키워드 (일반적인 키워드) */
const CATEGORY_TOPIC_KEYWORDS: Record<string, string[]> = {
  gaming: ["게임 리뷰", "공략", "실황", "e스포츠", "인디게임"],
  education: ["강의", "튜토리얼", "정리", "개념 설명", "팁"],
  food: ["레시피", "먹방", "요리", "맛집", "홈쿡"],
  fitness: ["운동법", "루틴", "다이어트", "스트레칭", "헬스"],
  art: ["그림", "디자인", "제작 과정", "팁", "튜토리얼"],
  music: ["커버", "제작기", "음악 이론", "장비", "작곡"],
  vlog: ["일상", "브이로그", "캠핑", "여행", "맛집"],
  business: ["창업", "마케팅", "재테크", "생산성", "경영"],
  entertainment: ["예능", "챌린지", "일상", "콜라보", "리액션"],
}

const CATEGORY_STYLE_KEYWORDS: Record<string, string[]> = {
  gaming: ["친근한", "유쾌한", "전문적", "몰입감", "캐주얼"],
  education: ["차분한", "전문적", "친절한", "구조적", "실용적"],
  food: ["따뜻한", "유쾌한", "감성", "실용적", "친근한"],
  fitness: ["에너지", "격려", "전문적", "간결한", "동기부여"],
  art: ["감성", "차분한", "창의적", "디테일", "몰입"],
  music: ["감성", "열정", "전문적", "캐주얼", "몽환적"],
  vlog: ["자연스러운", "친근한", "감성", "유쾌한", "솔직한"],
  business: ["전문적", "간결한", "신뢰감", "실용적", "명확한"],
  entertainment: ["유쾌한", "역동적", "친근한", "과장", "재미"],
}

/* Keyword Chip — 선택 시 primary, 미선택 시 muted */
interface KeywordChipProps {
  label: string
  isSelected: boolean
  onClick: () => void
}

function KeywordChip({ label, isSelected, onClick }: KeywordChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium border transition-all",
        isSelected
          ? "bg-primary/10 border-primary text-primary"
          : "bg-muted border-border text-muted-foreground hover:border-primary/20 hover:text-foreground"
      )}
    >
      {isSelected && <Check className="h-3.5 w-3.5" />}
      {label}
    </button>
  )
}

export interface StepChannelConceptProps {
  onNext: (data: { topicKeywords: string[]; styleKeywords: string[] }) => void
  onPrev: () => void
  initialData?: { topicKeywords?: string[]; styleKeywords?: string[] }
  /** Step 1에서 선택한 카테고리 ID 목록 (키워드 추천 소스) */
  selectedCategories?: string[]
  /** 카테고리 대신 직접 전달한 키워드 (있으면 이걸 사용) */
  suggestedKeywords?: { topics: string[]; styles: string[] }
}

export function StepChannelConcept({
  onNext,
  onPrev,
  initialData,
  selectedCategories = [],
  suggestedKeywords,
}: StepChannelConceptProps) {
  const [topicKeywords, setTopicKeywords] = useState<string[]>(
    initialData?.topicKeywords ?? []
  )
  const [styleKeywords, setStyleKeywords] = useState<string[]>(
    initialData?.styleKeywords ?? []
  )

  /* 선택된 카테고리 또는 suggestedKeywords 기반 옵션 (중복 제거) */
  const topicOptions = useMemo(() => {
    if (suggestedKeywords?.topics?.length) {
      return [...new Set(suggestedKeywords.topics)]
    }
    const keywords = selectedCategories.flatMap(
      (cat) => CATEGORY_TOPIC_KEYWORDS[cat] ?? []
    )
    return [...new Set(keywords)]
  }, [selectedCategories, suggestedKeywords?.topics])

  const styleOptions = useMemo(() => {
    if (suggestedKeywords?.styles?.length) {
      return [...new Set(suggestedKeywords.styles)]
    }
    const keywords = selectedCategories.flatMap(
      (cat) => CATEGORY_STYLE_KEYWORDS[cat] ?? []
    )
    return [...new Set(keywords)]
  }, [selectedCategories, suggestedKeywords?.styles])

  const handleToggleTopic = (keyword: string) => {
    setTopicKeywords((prev) => {
      if (prev.includes(keyword)) return prev.filter((k) => k !== keyword)
      if (prev.length >= 5) return prev
      return [...prev, keyword]
    })
  }

  const handleToggleStyle = (keyword: string) => {
    setStyleKeywords((prev) => {
      if (prev.includes(keyword)) return prev.filter((k) => k !== keyword)
      if (prev.length >= 5) return prev
      return [...prev, keyword]
    })
  }

  const handleNextClick = () => {
    if (topicKeywords.length >= 1 && styleKeywords.length >= 1) {
      onNext({ topicKeywords, styleKeywords })
    }
  }

  const isValid = topicKeywords.length >= 1 && styleKeywords.length >= 1

  return (
    <div className="animate-fade-in-up">
      {/* 헤딩 */}
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground mb-2 text-balance">
          채널의 방향성을 정해볼까요?
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed">
          주제 키워드와 분위기 키워드를 각각 1~5개 선택해주세요
        </p>
      </div>

      {/* 주제 키워드 */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <label className="text-sm font-semibold text-foreground">
            주제 키워드
          </label>
          <span className="text-xs text-muted-foreground">
            {topicKeywords.length}/5
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {topicOptions.map((keyword) => (
            <KeywordChip
              key={keyword}
              label={keyword}
              isSelected={topicKeywords.includes(keyword)}
              onClick={() => handleToggleTopic(keyword)}
            />
          ))}
        </div>
      </div>

      {/* 분위기 키워드 */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <label className="text-sm font-semibold text-foreground">
            분위기 키워드
          </label>
          <span className="text-xs text-muted-foreground">
            {styleKeywords.length}/5
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {styleOptions.map((keyword) => (
            <KeywordChip
              key={keyword}
              label={keyword}
              isSelected={styleKeywords.includes(keyword)}
              onClick={() => handleToggleStyle(keyword)}
            />
          ))}
        </div>
      </div>

      {/* 네비게이션 버튼 */}
      <div className="flex justify-between">
        <Button
          variant="ghost"
          onClick={onPrev}
          className="text-muted-foreground hover:text-foreground px-6 py-5 rounded-xl"
        >
          이전
        </Button>
        <Button
          onClick={handleNextClick}
          disabled={!isValid}
          className={cn(
            "px-8 py-5 rounded-xl text-base font-semibold transition-all",
            isValid
              ? "bg-gradient-to-br from-[#2D2DFF] to-primary text-primary-foreground hover:shadow-[0_8px_32px_rgba(107,92,255,0.35)] hover:-translate-y-0.5"
              : "opacity-40"
          )}
        >
          다음
        </Button>
      </div>
    </div>
  )
}
