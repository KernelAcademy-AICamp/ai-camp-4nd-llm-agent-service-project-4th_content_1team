"use client"

import React, { useState } from "react"
import { Button } from "../../../components/ui/button"
import { Badge } from "../../../components/ui/badge"
import {
  ChevronDown,
  TrendingUp,
  MessageCircle,
  LineChart,
  Lightbulb,
  Lock,
} from "lucide-react"
import { cn } from "../../../lib/utils"

/* 더미 분석 결과 데이터 */
const MOCK_RESULT = {
  channelName: "내 채널",
  mainTopics: ["게임", "리뷰", "공략"],
  toneSamples: ["~입니다 체", "친근한 반말", "감탄사 활용", "질문형 유도"],
  toneManner:
    "채널의 전반적인 어조는 친근하고 캐주얼한 톤을 유지하면서도 전문적인 내용 전달에 힘쓰는 스타일입니다. 시청자와의 거리감을 줄이기 위해 반말과 존댓말을 적절히 혼용하며, 감탄사와 질문형 문장을 통해 시청자 참여를 유도합니다.",
  successFormula:
    "문제 제기 → 솔루션 제시 → 실제 검증 패턴이 가장 높은 조회수를 기록했습니다",
  structureDetail:
    "조회수 상위 20% 영상의 공통 구조를 분석한 결과, 초반 30초 내 문제를 제기하고 중반에 솔루션을 제공하는 '문제-해결' 구조가 가장 효과적이었습니다.",
}

/* Section Card */
interface SectionCardProps {
  children: React.ReactNode
}

function SectionCard({ children }: SectionCardProps) {
  return (
    <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.02)] p-5 md:p-6">
      {children}
    </div>
  )
}

/* Section Header */
interface SectionHeaderProps {
  title: string
  subtitle: string
}

function SectionHeader({ title, subtitle }: SectionHeaderProps) {
  return (
    <div className="mb-5">
      <h2 className="text-lg font-bold text-foreground mb-1">{title}</h2>
      <p className="text-xs text-muted-foreground">{subtitle}</p>
    </div>
  )
}

/* 토글 섹션 */
interface ToggleSectionProps {
  title: string
  children: React.ReactNode
}

function ToggleSection({ title, children }: ToggleSectionProps) {
  const [isOpen, setIsOpen] = useState(false)

  const handleToggle = () => {
    setIsOpen((prev) => !prev)
  }

  return (
    <div
      className={cn(
        "rounded-lg border transition-all duration-300",
        isOpen
          ? "border-primary/15 bg-primary/[0.02]"
          : "border-[rgba(255,255,255,0.05)] bg-[rgba(255,255,255,0.01)]"
      )}
    >
      <button
        type="button"
        onClick={handleToggle}
        className="flex w-full items-center justify-between px-4 py-3 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <span className="font-medium">{title}</span>
        <ChevronDown
          className={cn("h-4 w-4 transition-transform duration-300", isOpen && "rotate-180")}
        />
      </button>
      {isOpen && <div className="px-4 pb-4">{children}</div>}
    </div>
  )
}

/* Topic Type Preview Card */
type TopicTypeColor = "green" | "blue" | "purple" | "amber"

interface TopicTypePreviewProps {
  color: TopicTypeColor
  icon: React.ElementType
  title: string
  detail: string
  isLocked?: boolean
}

const TOPIC_TYPE_COLOR_MAP: Record<
  TopicTypeColor,
  { border: string; bg: string; text: string; bar: string }
> = {
  green: {
    border: "border-green-500/20",
    bg: "bg-green-500/5",
    text: "text-green-500",
    bar: "from-green-500 to-green-700",
  },
  blue: {
    border: "border-blue-500/20",
    bg: "bg-blue-500/5",
    text: "text-blue-500",
    bar: "from-blue-500 to-blue-700",
  },
  purple: {
    border: "border-purple-500/20",
    bg: "bg-purple-500/5",
    text: "text-purple-500",
    bar: "from-purple-500 to-purple-700",
  },
  amber: {
    border: "border-amber-500/20",
    bg: "bg-amber-500/5",
    text: "text-amber-500",
    bar: "from-amber-500 to-amber-700",
  },
}

function TopicTypePreview({
  color,
  icon: Icon,
  title,
  detail,
  isLocked = false,
}: TopicTypePreviewProps) {
  const c = TOPIC_TYPE_COLOR_MAP[color]

  return (
    <div className={cn("p-4 rounded-lg border", c.border, c.bg, isLocked && "opacity-60")}>
      <div className="flex items-center gap-2 mb-2">
        <div className={cn("w-1 h-8 rounded bg-gradient-to-b", c.bar)} />
        <Icon className={cn("h-4 w-4 shrink-0", c.text)} />
        <div>
          <div className={cn("text-xs font-medium", c.text)}>{title}</div>
        </div>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{detail}</p>
    </div>
  )
}

/* 메인: 채널 분석 결과 화면 */
export interface ChannelAnalysisResultProps {
  onComplete: () => void
  hasCompetitors: boolean
}

export function ChannelAnalysisResult({ onComplete, hasCompetitors }: ChannelAnalysisResultProps) {
  return (
    <div className="max-w-[640px] mx-auto px-5 py-10">
      {/* Header */}
      <header className="mb-10 animate-fade-in-up">
        <Badge className="mb-3 bg-primary/10 text-primary border-primary/20 text-xs font-medium">
          Channel Analysis Complete
        </Badge>
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground mb-2 text-balance">
          {MOCK_RESULT.channelName}
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed mb-4">
          채널을 분석했어요. 앞으로 이렇게 도와드릴게요.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {MOCK_RESULT.mainTopics.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center px-3 py-1 rounded-md bg-primary/10 border border-primary/20 text-primary text-xs font-medium"
            >
              {tag}
            </span>
          ))}
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-foreground text-xs h-auto py-1 px-2"
          >
            수정
          </Button>
        </div>
      </header>

      {/* Section 1: 톤앤매너 */}
      <section className="mb-8 animate-fade-in-up animate-delay-1">
        <SectionCard>
          <SectionHeader
            title="이 톤으로 스크립트를 써드릴게요"
            subtitle="채널의 말투 패턴을 학습했어요"
          />
          <div className="bg-primary/5 border border-primary/10 rounded-lg p-4 mb-4">
            <div className="flex flex-wrap gap-2">
              {MOCK_RESULT.toneSamples.map((sample) => (
                <span
                  key={sample}
                  className="inline-flex items-center px-3 py-1.5 rounded-md bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-muted-foreground text-[13px] font-medium"
                >
                  {sample}
                </span>
              ))}
            </div>
          </div>
          <ToggleSection title="어떻게 분석했나요?">
            <p className="text-sm text-muted-foreground leading-relaxed">{MOCK_RESULT.toneManner}</p>
          </ToggleSection>
        </SectionCard>
      </section>

      {/* Section 2: 콘텐츠 구조 */}
      <section className="mb-8 animate-fade-in-up animate-delay-2">
        <SectionCard>
          <SectionHeader
            title="이 구조로 스크립트를 설계해드릴게요"
            subtitle="조회수가 높았던 영상의 공통 구조를 분석했어요"
          />
          <div className="relative rounded-lg p-4 mb-4 overflow-hidden bg-gradient-to-r from-primary/10 to-green-500/5 border border-primary/20">
            <div className="h-0.5 bg-gradient-to-r from-primary to-green-500 rounded-full mb-3" />
            <p className="text-xs text-muted-foreground uppercase font-medium tracking-wider mb-1">
              성공 공식
            </p>
            <p className="text-sm font-semibold text-foreground leading-relaxed">
              {MOCK_RESULT.successFormula}
            </p>
          </div>
          <ToggleSection title="어떻게 분석했나요?">
            <p className="text-sm text-muted-foreground leading-relaxed">
              {MOCK_RESULT.structureDetail}
            </p>
          </ToggleSection>
        </SectionCard>
      </section>

      {/* Section 3: 추천 주제 미리보기 */}
      <section className="mb-8 animate-fade-in-up animate-delay-3">
        <SectionCard>
          <SectionHeader
            title="이렇게 주제를 추천해드릴게요"
            subtitle="분석 결과를 바탕으로 4가지 방식으로 주제를 찾아드려요"
          />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <TopicTypePreview
              color="green"
              icon={TrendingUp}
              title="성공 방정식"
              detail="조회수가 높았던 영상의 패턴을 분석해서 유사한 주제를 추천해요"
            />
            <TopicTypePreview
              color="blue"
              icon={MessageCircle}
              title="구독자 관심"
              detail="시청자들이 가장 궁금해하는 질문을 주제로 만들어요"
            />
            <TopicTypePreview
              color="purple"
              icon={LineChart}
              title="최근 경향성"
              detail="최근 인기 있었던 영상 스타일로 새로운 시도를 제안해요"
            />
            <TopicTypePreview
              color="amber"
              icon={hasCompetitors ? Lightbulb : Lock}
              title="차별화 기회"
              detail={
                hasCompetitors
                  ? "경쟁 채널 분석 결과 틈새 시장을 찾아드려요"
                  : "지향 유튜버를 추가하면 경쟁 분석 기반 추천이 활성화돼요"
              }
              isLocked={!hasCompetitors}
            />
          </div>
        </SectionCard>
      </section>

      {/* 경쟁 채널 백그라운드 분석 안내 */}
      {hasCompetitors && (
        <section className="mb-8 animate-fade-in-up animate-delay-4">
          <div className="flex items-center gap-3 px-4 py-3.5 rounded-xl bg-amber-500/5 border border-amber-500/15">
            <div className="h-2 w-2 rounded-full bg-amber-500 animate-pulse shrink-0" />
            <p className="text-xs text-muted-foreground leading-relaxed">
              경쟁 채널 분석이 백그라운드에서 진행 중이에요. 완료되면 &apos;차별화 기회&apos; 추천이
              자동으로 업데이트됩니다.
            </p>
          </div>
        </section>
      )}

      {/* CTA */}
      <div className="animate-fade-in-up animate-delay-4">
        <Button
          onClick={onComplete}
          className="w-full py-5 rounded-xl text-base font-semibold bg-gradient-to-br from-[#2D2DFF] to-primary text-primary-foreground hover:shadow-[0_8px_32px_rgba(107,92,255,0.35)] hover:-translate-y-0.5 transition-all"
          size="lg"
        >
          이 분석 기반으로 주제 추천받기
        </Button>
        <p className="text-xs text-muted-foreground text-center mt-3">
          분석 결과는 언제든 수정할 수 있어요
        </p>
      </div>
    </div>
  )
}
