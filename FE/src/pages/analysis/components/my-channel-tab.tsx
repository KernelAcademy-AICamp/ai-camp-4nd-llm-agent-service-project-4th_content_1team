"use client"

import { useNavigate } from "react-router-dom"
import { Loader2, Users, Target, Sparkles, TrendingUp, Video } from "lucide-react"
import { Button } from "../../../components/ui/button"
import { useQuery } from "@tanstack/react-query"
import { getMyPersona } from "../../../lib/api/services"
import {
  SectionCard,
  SectionHeader,
  ToggleSection,
} from "../../onboarding/components/channel-analysis-result"

export function MyChannelTab() {
  const navigate = useNavigate()
  const { data: persona, isLoading, isError } = useQuery({
    queryKey: ["my-persona"],
    queryFn: getMyPersona,
    staleTime: 1000 * 60 * 10,
  })

  /* 로딩 */
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  /* 에러 또는 데이터 없음 */
  if (isError || !persona) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Users className="w-12 h-12 text-muted-foreground mb-4" />
        <h3 className="font-medium text-foreground mb-2">
          아직 채널 분석이 완료되지 않았습니다
        </h3>
        <p className="text-sm text-muted-foreground max-w-[300px]">
          온보딩에서 채널 분석을 먼저 진행해주세요
        </p>
      </div>
    )
  }

  /* Branch B: 자막 분석 데이터가 없는 경우 (수동 온보딩) */
  const hasDetailedAnalysis = !!(
    persona.tone_manner ||
    persona.success_formula ||
    (persona.video_types && Object.keys(persona.video_types).length > 0)
  )

  if (!hasDetailedAnalysis) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Video className="w-12 h-12 text-muted-foreground mb-4" />
        <h3 className="font-medium text-foreground mb-2">
          아직 정보가 충분하지 않아요
        </h3>
        <p className="text-sm text-muted-foreground max-w-[340px] mb-6">
          영상이 좀 더 쌓인다면 분석할 수 있어요!<br />
          저와 함께 만들어 봐요
        </p>
        <Button
          onClick={() => navigate("/explore")}
          className="rounded-xl px-6 py-3 text-sm font-semibold bg-gradient-to-br from-[#2D2DFF] to-primary text-primary-foreground hover:shadow-[0_8px_32px_rgba(107,92,255,0.35)] hover:-translate-y-0.5 transition-all"
        >
          주제 탐색하러 가기
        </Button>
      </div>
    )
  }

  const mainTopics = persona.main_topics || []
  const contentStyles = persona.content_style ? persona.content_style.split(",").map(s => s.trim()).filter(Boolean) : []
  const toneSamples = persona.tone_samples || []
  const hitPatterns = persona.hit_patterns || []
  const videoTypes = persona.video_types || {}
  const contentStructures = persona.content_structures || {}
  const growthOpportunities = persona.growth_opportunities || []

  return (
    <div className="max-w-[900px] mx-auto py-6 space-y-6">
      {/* 헤더: 채널명 + 주제 태그 */}
      <header>
        <h2 className="text-2xl font-extrabold tracking-tight text-foreground mb-2">
          {persona.one_liner || "내 채널"}
        </h2>
        {mainTopics.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {mainTopics.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center px-3 py-1 rounded-md bg-primary/10 border border-primary/20 text-primary text-xs font-medium"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </header>

      {/* Section 1: 채널 요약 */}
      {persona.persona_summary && (
        <section>
          <SectionCard>
            <SectionHeader
              title="채널 요약"
              subtitle="AI가 분석한 채널의 전체적인 특성이에요"
            />
            <p className="text-sm text-muted-foreground leading-relaxed mb-4">
              {persona.persona_summary}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {persona.target_audience && (
                <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/15">
                  <Target className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-blue-500 mb-1">타겟 시청자</p>
                    <p className="text-sm text-muted-foreground">{persona.target_audience}</p>
                  </div>
                </div>
              )}
              {persona.differentiator && (
                <div className="flex items-start gap-3 p-3 rounded-lg bg-purple-500/5 border border-purple-500/15">
                  <Sparkles className="w-4 h-4 text-purple-500 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-purple-500 mb-1">차별화 포인트</p>
                    <p className="text-sm text-muted-foreground">{persona.differentiator}</p>
                  </div>
                </div>
              )}
            </div>
          </SectionCard>
        </section>
      )}

      {/* Section 2: 톤앤매너 */}
      {(contentStyles.length > 0 || toneSamples.length > 0) && (
        <section>
          <SectionCard>
            <SectionHeader
              title="톤앤매너"
              subtitle="채널의 말투 패턴을 학습했어요"
            />
            <div className="bg-primary/5 border border-primary/10 rounded-lg p-4 mb-4">
              {contentStyles.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {contentStyles.map((style) => (
                    <span
                      key={style.trim()}
                      className="inline-flex items-center px-3 py-1.5 rounded-md bg-primary/10 border border-primary/20 text-primary text-xs font-medium"
                    >
                      {style.trim()}
                    </span>
                  ))}
                </div>
              )}
              {toneSamples.length > 0 && (
                <div className="space-y-1.5">
                  {toneSamples.slice(0, 3).map((sample) => (
                    <p
                      key={sample}
                      className="text-[13px] text-muted-foreground leading-relaxed"
                    >
                      &ldquo;{sample}&rdquo;
                    </p>
                  ))}
                </div>
              )}
            </div>
            {persona.tone_manner && (
              <ToggleSection title="어떻게 분석했나요?">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {persona.tone_manner}
                </p>
              </ToggleSection>
            )}
          </SectionCard>
        </section>
      )}

      {/* Section 3: 콘텐츠 구조 */}
      {(persona.success_formula || hitPatterns.length > 0) && (
        <section>
          <SectionCard>
            <SectionHeader
              title="콘텐츠 구조"
              subtitle="조회수가 높았던 영상의 공통 패턴을 분석했어요"
            />
            <div className="relative rounded-lg p-4 mb-4 overflow-hidden bg-gradient-to-r from-primary/10 to-green-500/5 border border-primary/20">
              <div className="h-0.5 bg-gradient-to-r from-primary to-green-500 rounded-full mb-3" />
              <p className="text-xs text-muted-foreground uppercase font-medium tracking-wider mb-2">
                성공 공식
              </p>
              {hitPatterns.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {hitPatterns.slice(0, 3).map((pattern) => (
                    <span
                      key={pattern}
                      className="inline-flex items-center px-2.5 py-1 rounded-md bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.1)] text-xs font-medium text-foreground/80"
                    >
                      {pattern}
                    </span>
                  ))}
                </div>
              )}
              {persona.success_formula && (
                <p className="text-sm font-semibold text-foreground leading-relaxed">
                  {persona.success_formula}
                </p>
              )}
            </div>
            {Object.keys(videoTypes).length > 0 && (
              <ToggleSection title="어떻게 분석했나요?">
                <div className="space-y-4">
                  {Object.entries(videoTypes)
                    .sort(([, a], [, b]) => b - a)
                    .map(([type, percent]) => (
                      <div key={type}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-semibold text-foreground">{type}</span>
                          <span className="text-xs text-muted-foreground">({percent}%)</span>
                        </div>
                        {contentStructures[type] && (
                          <p className="text-xs text-muted-foreground leading-relaxed pl-1">
                            {contentStructures[type]}
                          </p>
                        )}
                      </div>
                    ))}
                </div>
              </ToggleSection>
            )}
          </SectionCard>
        </section>
      )}

      {/* Section 4: 성장 기회 */}
      {growthOpportunities.length > 0 && (
        <section>
          <SectionCard>
            <SectionHeader
              title="성장 기회"
              subtitle="채널이 더 성장할 수 있는 방향이에요"
            />
            <div className="space-y-3">
              {growthOpportunities.map((opportunity, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/15"
                >
                  <TrendingUp className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                  <p className="text-sm text-muted-foreground">{opportunity}</p>
                </div>
              ))}
            </div>
          </SectionCard>
        </section>
      )}
    </div>
  )
}
