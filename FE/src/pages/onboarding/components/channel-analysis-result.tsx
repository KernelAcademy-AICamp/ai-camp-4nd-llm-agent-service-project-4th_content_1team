"use client"

import React, { useState } from "react"
import { Button } from "../../../components/ui/button"
import { Badge } from "../../../components/ui/badge"
import { useAuth } from "../../../hooks/useAuth"
import {
  ChevronDown,
  TrendingUp,
  MessageCircle,
  LineChart,
} from "lucide-react"
import { cn } from "../../../lib/utils"

/* 추천 주제 미리보기 타입 */
export interface TrendPreviewItem {
  type: "hit_pattern" | "viewer_needs" | "trend_driven"
  topicTitle: string
  reason: string
}

/* 분석 결과 데이터 타입 */
export interface AnalysisResultData {
  channelName: string
  mainTopics: string[]
  contentStyle: string
  toneSamples: string[]
  toneManner: string
  successFormula: string
  hitPatterns: string[]
  videoTypes: Record<string, number>
  contentStructures: Record<string, string>
  trendPreviews: TrendPreviewItem[]
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
  topicTitle?: string
  detail: string
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
  topicTitle,
  detail,
}: TopicTypePreviewProps) {
  const c = TOPIC_TYPE_COLOR_MAP[color]

  return (
    <div className={cn("p-4 rounded-lg border", c.border, c.bg)}>
      <div className="flex items-center gap-2 mb-2">
        <div className={cn("w-1 h-8 rounded bg-gradient-to-b", c.bar)} />
        <Icon className={cn("h-4 w-4 shrink-0", c.text)} />
        <div>
          <div className={cn("text-xs font-medium", c.text)}>{title}</div>
        </div>
      </div>
      {topicTitle && (
        <p className="text-sm font-semibold text-foreground mb-1.5 leading-snug">{topicTitle}</p>
      )}
      <p className="text-xs text-muted-foreground leading-relaxed">{detail}</p>
    </div>
  )
}

/* 추천 타입별 카드 설정 */
const RECOMMENDATION_TYPE_CONFIG: Record<
  TrendPreviewItem["type"],
  { color: TopicTypeColor; icon: React.ElementType; label: string }
> = {
  hit_pattern: { color: "green", icon: TrendingUp, label: "성공 방정식" },
  viewer_needs: { color: "blue", icon: MessageCircle, label: "구독자 관심" },
  trend_driven: { color: "purple", icon: LineChart, label: "최근 경향성" },
}

/* 메인: 채널 분석 결과 화면 */
export interface ChannelAnalysisResultProps {
  onComplete: () => void
  hasCompetitors: boolean
  data: AnalysisResultData
}

export function ChannelAnalysisResult({ onComplete, hasCompetitors, data }: ChannelAnalysisResultProps) {
  const { user } = useAuth()
  const profileImage = user?.avatar_url || "/profile_dummy.png"
  const userName = user?.name || "사용자"

  return (
    <div className="max-w-[640px] mx-auto px-5 py-10">
      {/* Header */}
      <header className="mb-4 animate-fade-in-up">
        <Badge className="mb-3 bg-primary/10 text-primary border-primary/20 text-xs font-medium">
          Channel Analysis Complete
        </Badge>
        <div className="flex items-center gap-3 mb-3">
          <img
            src={profileImage}
            alt={userName}
            className="w-10 h-10 rounded-full object-cover border border-[rgba(255,255,255,0.1)]"
          />
          <p className="text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">{userName}</span>의 페르소나입니다
          </p>
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground mb-2 text-balance">
          {data.channelName}
        </h1>
        <div className="flex flex-wrap items-center gap-2">
          {data.mainTopics.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center px-3 py-1 rounded-md bg-primary/10 border border-primary/20 text-primary text-xs font-medium"
            >
              {tag}
            </span>
          ))}
        </div>
        <p className="text-sm text-muted-foreground leading-relaxed mt-6">
          앞으로 이렇게 도와드릴게요.
        </p>
      </header>

      {/* Section 1: 톤앤매너 */}
      <section className="mb-8 animate-fade-in-up animate-delay-1">
        <SectionCard>
          <SectionHeader
            title="이 톤으로 스크립트를 써드릴게요"
            subtitle="채널의 말투 패턴을 학습했어요"
          />
          <div className="bg-primary/5 border border-primary/10 rounded-lg p-4 mb-4">
            {/* 콘텐츠 스타일 태그 */}
            <div className="flex flex-wrap gap-2 mb-3">
              {data.contentStyle.split(",").map((style) => (
                <span
                  key={style.trim()}
                  className="inline-flex items-center px-3 py-1.5 rounded-md bg-primary/10 border border-primary/20 text-primary text-xs font-medium"
                >
                  {style.trim()}
                </span>
              ))}
            </div>
            {/* 말투 샘플 (최대 3개) */}
            <div className="space-y-1.5">
              {data.toneSamples.slice(0, 3).map((sample) => (
                <p
                  key={sample}
                  className="text-[13px] text-muted-foreground leading-relaxed"
                >
                  &ldquo;{sample}&rdquo;
                </p>
              ))}
            </div>
          </div>
          <ToggleSection title="어떻게 분석했나요?">
            <p className="text-sm text-muted-foreground leading-relaxed">{data.toneManner}</p>
          </ToggleSection>
        </SectionCard>
      </section>

      {/* Section 2: 콘텐츠 구조 */}
      <section className="mb-8 animate-fade-in-up animate-delay-2">
        <SectionCard>
          <SectionHeader
            title="이 구조로 스크립트를 설계해드릴게요"
            subtitle="조회수가 높았던 영상의 공통 패턴을 분석했어요"
          />
          <div className="relative rounded-lg p-4 mb-4 overflow-hidden bg-gradient-to-r from-primary/10 to-green-500/5 border border-primary/20">
            <div className="h-0.5 bg-gradient-to-r from-primary to-green-500 rounded-full mb-3" />
            <p className="text-xs text-muted-foreground uppercase font-medium tracking-wider mb-2">
              성공 공식
            </p>
            {data.hitPatterns.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {data.hitPatterns.slice(0, 3).map((pattern) => (
                  <span
                    key={pattern}
                    className="inline-flex items-center px-2.5 py-1 rounded-md bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.1)] text-xs font-medium text-foreground/80"
                  >
                    {pattern}
                  </span>
                ))}
              </div>
            )}
            <p className="text-sm font-semibold text-foreground leading-relaxed">
              {data.successFormula}
            </p>
          </div>
          <ToggleSection title="어떻게 분석했나요?">
            <div className="space-y-4">
              {Object.entries(data.videoTypes)
                .sort(([, a], [, b]) => b - a)
                .map(([type, percent]) => (
                  <div key={type}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-foreground">{type}</span>
                      <span className="text-xs text-muted-foreground">({percent}%)</span>
                    </div>
                    {data.contentStructures[type] && (
                      <p className="text-xs text-muted-foreground leading-relaxed pl-1">
                        {data.contentStructures[type]}
                      </p>
                    )}
                  </div>
                ))}
            </div>
          </ToggleSection>
        </SectionCard>
      </section>

      {/* Section 3: 추천 주제 미리보기 */}
      {data.trendPreviews.length > 0 && (
        <section className="mb-8 animate-fade-in-up animate-delay-3">
          <SectionCard>
            <SectionHeader
              title="이렇게 주제를 추천해드릴게요"
              subtitle="분석 결과를 바탕으로 주제를 찾아드렸어요"
            />
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
              {data.trendPreviews.map((preview) => {
                const config = RECOMMENDATION_TYPE_CONFIG[preview.type]
                return (
                  <TopicTypePreview
                    key={preview.type}
                    color={config.color}
                    icon={config.icon}
                    title={config.label}
                    topicTitle={preview.topicTitle}
                    detail={preview.reason}
                  />
                )
              })}
            </div>
          </SectionCard>
        </section>
      )}

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
          주제 탐색하러 가기
        </Button>
      </div>
    </div>
  )
}
