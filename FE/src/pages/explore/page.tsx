import { useState, useEffect, useRef } from "react"
import { Loader2 } from "lucide-react"
import { TopicCard } from "./components/topic-card"
import { TopicDetailSidebar } from "./components/topic-detail-sidebar"
import { useSidebar } from "../../contexts/sidebar-context"
import { getTopics } from "../../lib/api/services"
import type { TopicResponse } from "../../lib/api/types"

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
  // 사이드바 추가 정보
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

// 기존 Topic 인터페이스 (목데이터 섹션용)
interface Topic {
  id: string
  badge: string
  title: string
  description: string
  hashtags: string[]
}

// Mock 데이터 - 경쟁 채널보다 다르게 (나중에 API 연결)
const MOCK_DIFFERENTIATE_TOPICS: Topic[] = [
  {
    id: "5",
    badge: "차별화 기회",
    title: "경쟁사가 놓친 틈새 시장 공략",
    description: "경쟁 채널들이 다루지 않는 주제로 새로운 시청자층을 확보하세요!",
    hashtags: ["차별화", "틈새", "전략"],
  },
  {
    id: "6",
    badge: "차별화 기회",
    title: "시청자들이 원하지만 없는 콘텐츠",
    description: "댓글과 검색 데이터를 분석해서 수요는 있지만 공급이 부족한 주제를 찾았어요!",
    hashtags: ["수요분석", "콘텐츠기획", "기회"],
  },
  {
    id: "7",
    badge: "차별화 기회",
    title: "트렌드를 거꾸로 활용하는 역발상",
    description: "모두가 따라하는 트렌드를 반대로 접근해서 주목받는 방법!",
    hashtags: ["역발상", "독창성", "트렌드"],
  },
  {
    id: "8",
    badge: "차별화 기회",
    title: "경쟁 채널의 약점을 내 강점으로",
    description: "경쟁 채널 분석 결과, 시청자들이 아쉬워하는 부분을 찾아냈어요!",
    hashtags: ["경쟁분석", "강점", "개선"],
  },
]

export default function ExplorePage() {
  const { isDetailSidebarOpen, openDetailSidebar } = useSidebar()
  const [selectedTopic, setSelectedTopic] = useState<DisplayTopic | null>(null)

  // 트렌드 추천 API 상태
  const [trendTopics, setTrendTopics] = useState<DisplayTopic[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const hasCalledRef = useRef(false)

  // 트렌드 추천 조회
  useEffect(() => {
    if (hasCalledRef.current) return
    hasCalledRef.current = true

    const fetchTopics = async () => {
      try {
        setIsLoading(true)
        setLoadError(null)
        const response = await getTopics()
        const mapped = response.trend_topics.map(toDisplayTopic)
        setTrendTopics(mapped)
      } catch (err: any) {
        console.error("트렌드 추천 조회 실패:", err)
        setLoadError("추천 주제를 불러오는데 실패했습니다.")
      } finally {
        setIsLoading(false)
      }
    }

    fetchTopics()
  }, [])

  // 트렌드 주제 카드 클릭 핸들러
  const handleTrendTopicClick = (topic: DisplayTopic) => {
    setSelectedTopic(topic)
    openDetailSidebar()
  }

  // 목데이터 주제 카드 클릭 핸들러
  const handleMockTopicClick = (topic: Topic) => {
    setSelectedTopic({
      ...topic,
      recommendation_direction: "",
      content_angles: [],
      trend_basis: "",
      thumbnail_idea: "",
      urgency: "normal",
      source_layer: "core",
      topic_type: "channel",
    })
    openDetailSidebar()
  }

  return (
    <div className="min-h-full w-full bg-background px-4 py-6 md:p-6">
      {/* 전체 컨테이너 */}
      <div className="max-w-[1352px] mx-auto">
        {/* 헤더 컨테이너 */}
        <div className="mb-8 md:mb-10">
          <h1 className="text-2xl md:text-3xl font-semibold text-foreground mb-2">
            주제 탐색
          </h1>
          <p className="text-sm md:text-base text-muted-foreground">
            AI가 당신의 채널에 딱 맞는 주제를 찾았어요
          </p>
        </div>

        {/* 섹션들 컨테이너 */}
        <div className="space-y-12">
          {/* 내 채널 강점 키우기 - API 연결 */}
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-6">
              내 채널 강점 키우기
            </h2>

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

            {!isLoading && !loadError && trendTopics.length === 0 && (
              <div className="text-center py-12">
                <p className="text-muted-foreground">아직 추천된 주제가 없어요. 잠시 후 다시 확인해 주세요.</p>
              </div>
            )}

            {!isLoading && !loadError && trendTopics.length > 0 && (
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
                    onClick={() => handleTrendTopicClick(topic)}
                  />
                ))}
              </div>
            )}
          </section>

          {/* 경쟁 채널과 다르게 - 목데이터 유지 */}
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-6">
              경쟁 채널과 다르게
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {MOCK_DIFFERENTIATE_TOPICS.map((topic) => (
                <TopicCard
                  key={topic.id}
                  id={topic.id}
                  badge={topic.badge}
                  title={topic.title}
                  description={topic.description}
                  hashtags={topic.hashtags}
                  onClick={() => handleMockTopicClick(topic)}
                />
              ))}
            </div>
          </section>
        </div>
      </div>

      {/* 상세 정보 사이드바 */}
      {isDetailSidebarOpen && selectedTopic && (
        <TopicDetailSidebar topic={selectedTopic} />
      )}
    </div>
  )
}
