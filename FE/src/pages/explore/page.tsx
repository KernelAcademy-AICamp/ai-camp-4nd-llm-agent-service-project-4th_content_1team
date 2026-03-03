import { useState, useEffect, useRef } from "react"
import { Loader2 } from "lucide-react"
import { TopicCard } from "./components/topic-card"
import { TopicDetailSidebar } from "./components/topic-detail-sidebar"
import { useSidebar } from "../../contexts/sidebar-context"
import { getTopics, skipTopic, generateTrendTopics, generateCompetitorTopics } from "../../lib/api/services"
import type { TopicResponse } from "../../lib/api/types"

const TOPIC_MIN = 4        // 카테고리별 최소 주제 수
const POLL_INTERVAL_MS = 5000
const POLL_MAX_ATTEMPTS = 20

// recommendation_type → badge 매핑
const BADGE_MAP: Record<string, string> = {
  hit_pattern: "성공 방정식",
  viewer_needs: "구독자 관심",
  trend_driven: "최근 경향성",
}

// TopicResponse → 카드 표시용 인터페이스
export interface DisplayTopic {
  id: string
  badge: string
  title: string
  description: string
  hashtags: string[]
  recommendation_direction: string
  content_angles: string[]
  trend_basis: string
  thumbnail_idea: string
  urgency: string
  source_layer: string
  topic_type: string
}

// TopicResponse → DisplayTopic 변환
function toDisplayTopic(topic: TopicResponse): DisplayTopic {
  return {
    id: topic.id,
    badge: BADGE_MAP[topic.recommendation_type || ""] || "AI 추천",
    title: topic.title,
    description: topic.recommendation_reason || "",
    hashtags: topic.search_keywords || [],
    recommendation_direction: topic.recommendation_direction || "",
    content_angles: topic.content_angles || [],
    trend_basis: topic.trend_basis || "",
    thumbnail_idea: topic.thumbnail_idea || "",
    urgency: topic.urgency || "normal",
    source_layer: topic.source_layer || "core",
    topic_type: topic.topic_type || "trend",
  }
}

// 경쟁자 분석 기반 추천인지 확인
function isCompetitorBasedTopic(topic: TopicResponse): boolean {
  return topic.based_on_topic?.startsWith("competitor_analysis") ?? false
}

export default function ExplorePage() {
  const { isDetailSidebarOpen, openDetailSidebar } = useSidebar()
  const [selectedTopic, setSelectedTopic] = useState<DisplayTopic | null>(null)

  const [trendTopics, setTrendTopics] = useState<DisplayTopic[]>([])
  const [competitorTopics, setCompetitorTopics] = useState<DisplayTopic[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollAttemptRef = useRef(0)

  const fetchAndSetTopics = async (): Promise<{ trendCount: number; competitorCount: number }> => {
    const response = await getTopics()
    const allTopics = [...response.channel_topics, ...response.trend_topics]
    const competitorBased = allTopics.filter(isCompetitorBasedTopic)
    const otherTopics = allTopics.filter((t) => !isCompetitorBasedTopic(t))
    setCompetitorTopics(competitorBased.map(toDisplayTopic))
    setTrendTopics(otherTopics.map(toDisplayTopic))
    return { trendCount: otherTopics.length, competitorCount: competitorBased.length }
  }

  const startPolling = () => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    pollAttemptRef.current = 0

    pollTimerRef.current = setInterval(async () => {
      pollAttemptRef.current += 1
      if (pollAttemptRef.current > POLL_MAX_ATTEMPTS) {
        setIsSearching(false)
        clearInterval(pollTimerRef.current!)
        return
      }
      try {
        const { trendCount, competitorCount } = await fetchAndSetTopics()
        if (trendCount >= TOPIC_MIN && competitorCount >= TOPIC_MIN) {
          setIsSearching(false)
          clearInterval(pollTimerRef.current!)
        }
      } catch {
        // 폴링 실패 무시, 계속 시도
      }
    }, POLL_INTERVAL_MS)
  }

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true)
        setLoadError(null)
        const { trendCount, competitorCount } = await fetchAndSetTopics()

        if (trendCount < TOPIC_MIN || competitorCount < TOPIC_MIN) {
          setIsSearching(true)
          if (trendCount < TOPIC_MIN) {
            generateTrendTopics().catch(() => {})
          }
          if (competitorCount < TOPIC_MIN) {
            generateCompetitorTopics().catch(() => {})
          }
          startPolling()
        }
      } catch (err: any) {
        console.error("추천 조회 실패:", err)
        setLoadError("추천 주제를 불러오는데 실패했습니다.")
      } finally {
        setIsLoading(false)
      }
    }
    load()

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    }
  }, [])

  const handleTopicClick = (topic: DisplayTopic) => {
    setSelectedTopic(topic)
    openDetailSidebar()
  }

  const handleScriptWrite = async (topicId: string, topicType: string, isCompetitor: boolean) => {
    try {
      const type = topicType === "channel" ? "channel" : "trend"
      const result = await skipTopic(type, topicId)
      const newTopic = result.new_topic ? toDisplayTopic(result.new_topic as TopicResponse) : null

      if (isCompetitor) {
        setCompetitorTopics((prev) => {
          const filtered = prev.filter((t) => t.id !== topicId)
          return newTopic ? [...filtered, newTopic] : filtered
        })
      } else {
        setTrendTopics((prev) => {
          const filtered = prev.filter((t) => t.id !== topicId)
          return newTopic ? [...filtered, newTopic] : filtered
        })
      }
    } catch (err) {
      console.error("주제 skip 실패:", err)
    }
  }

  return (
    <div className="min-h-full w-full bg-background px-4 py-6 md:p-6">
      <div className="max-w-[1352px] mx-auto">
        {/* 헤더 */}
        <div className="mb-8 md:mb-10">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl md:text-3xl font-semibold text-foreground">
              주제 탐색
            </h1>
            {isSearching && (
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                주제 탐색 중입니다...
              </span>
            )}
          </div>
          <p className="text-sm md:text-base text-muted-foreground">
            AI가 당신의 채널에 딱 맞는 주제를 찾았어요
          </p>
        </div>

        <div className="space-y-12">
          {/* 내 채널 강점 키우기 */}
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-6">내 채널 강점 키우기</h2>

            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
                <span className="ml-3 text-muted-foreground">추천 주제를 불러오고 있어요...</span>
              </div>
            )}

            {!isLoading && loadError && (
              <div className="text-center py-12">
                <p className="text-muted-foreground">{loadError}</p>
              </div>
            )}

            {!isLoading && !loadError && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {trendTopics.map((topic) => (
                  <TopicCard
                    key={topic.id}
                    id={topic.id}
                    badge={topic.badge}
                    title={topic.title}
                    description={topic.description}
                    hashtags={topic.hashtags}
                    topicId={topic.id}
                    topicType={topic.topic_type}
                    onClick={() => handleTopicClick(topic)}
                    onScriptWrite={() => handleScriptWrite(topic.id, topic.topic_type, false)}
                  />
                ))}

                {/* 빈 슬롯 스켈레톤 (탐색 중일 때) */}
                {isSearching && trendTopics.length < TOPIC_MIN &&
                  Array.from({ length: TOPIC_MIN - trendTopics.length }).map((_, i) => (
                    <div
                      key={`skeleton-trend-${i}`}
                      className="relative w-full h-[282px] rounded-[10px] bg-[#1e293b] animate-pulse flex items-center justify-center"
                    >
                      <div className="flex flex-col items-center gap-2 text-muted-foreground/50">
                        <Loader2 className="w-6 h-6 animate-spin" />
                        <span className="text-xs">주제 탐색 중...</span>
                      </div>
                    </div>
                  ))
                }

                {!isSearching && trendTopics.length === 0 && (
                  <div className="col-span-4 text-center py-12">
                    <p className="text-muted-foreground">아직 추천된 주제가 없어요. 잠시 후 다시 확인해 주세요.</p>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* 경쟁 채널과 다르게 */}
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-6">경쟁 채널과 다르게</h2>

            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
                <span className="ml-3 text-muted-foreground">경쟁자 분석 추천을 불러오고 있어요...</span>
              </div>
            )}

            {!isLoading && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {competitorTopics.map((topic) => (
                  <TopicCard
                    key={topic.id}
                    id={topic.id}
                    badge="차별화 기회"
                    title={topic.title}
                    description={topic.trend_basis || topic.description}
                    hashtags={topic.hashtags}
                    topicId={topic.id}
                    topicType={topic.topic_type}
                    onClick={() => handleTopicClick(topic)}
                    onScriptWrite={() => handleScriptWrite(topic.id, topic.topic_type, true)}
                  />
                ))}

                {/* 빈 슬롯 스켈레톤 (탐색 중일 때) */}
                {isSearching && competitorTopics.length < TOPIC_MIN &&
                  Array.from({ length: TOPIC_MIN - competitorTopics.length }).map((_, i) => (
                    <div
                      key={`skeleton-comp-${i}`}
                      className="relative w-full h-[282px] rounded-[10px] bg-[#1e293b] animate-pulse flex items-center justify-center"
                    >
                      <div className="flex flex-col items-center gap-2 text-muted-foreground/50">
                        <Loader2 className="w-6 h-6 animate-spin" />
                        <span className="text-xs">주제 탐색 중...</span>
                      </div>
                    </div>
                  ))
                }

                {!isSearching && competitorTopics.length === 0 && (
                  <div className="col-span-4 text-center py-12">
                    <p className="text-muted-foreground">경쟁자 분석 기반 추천이 없어요. 경쟁 채널을 등록하고 분석해 보세요.</p>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>

      {isDetailSidebarOpen && selectedTopic && (
        <TopicDetailSidebar topic={selectedTopic} />
      )}
    </div>
  )
}
