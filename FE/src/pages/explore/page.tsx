import { useState } from "react"
import { useSidebar } from "@/contexts/sidebar-context"
import { TopicCard } from "./components/topic-card"
import { TopicDetailSidebar } from "./components/topic-detail-sidebar"

interface Topic {
  id: string
  badge: string
  title: string
  description: string
  hashtags: string[]
}

// Mock 데이터 - 내 채널 강점 키우기
const MOCK_GROWTH_TOPICS: Topic[] = [
  {
    id: "1",
    badge: "성공 방정식",
    title: "실패했던 프로젝트에서 배운 5가지 교훈",
    description: "경쟁 채널들은 성공 스토리만 다루는데, 실패담으로 차별화하면 더 진정성 있게 다가갈 수 있어요!",
    hashtags: ["창업", "실패극복", "진솔한이야기"],
  },
  {
    id: "2",
    badge: "구독자 관심",
    title: "구독자가 가장 궁금해하는 질문 TOP 5",
    description: "댓글 분석 결과, 구독자들이 가장 많이 물어보는 질문들을 정리했어요!",
    hashtags: ["구독자", "소통", "Q&A"],
  },
  {
    id: "3",
    badge: "최근 경향성",
    title: "최근 영상 스타일로 새로운 시도",
    description: "최근 인기 있었던 영상 패턴을 분석해서 다음 콘텐츠 아이디어를 제안해요!",
    hashtags: ["트렌드", "영상분석", "새시도"],
  },
  {
    id: "4",
    badge: "성공 방정식",
    title: "지난 히트작 공식 재현하기",
    description: "과거 인기 영상의 성공 요소를 분석해서 다시 한번 적용해보세요!",
    hashtags: ["히트작", "성공패턴", "재현"],
  },
]

// Mock 데이터 - 경쟁 채널보다 다르게
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
  const { openDetailSidebar, closeDetailSidebar } = useSidebar()
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null)

  const handleTopicClick = (topic: Topic) => {
    setSelectedTopic(topic)
    openDetailSidebar()
  }

  const handleCloseDetail = () => {
    closeDetailSidebar()
    setSelectedTopic(null)
  }

  return (
    <div className="min-h-full w-full px-4 py-6 md:p-6">
      <div className="max-w-[1352px] mx-auto">
        <div className="mb-8 md:mb-10">
          <h1 className="text-2xl md:text-3xl font-semibold text-foreground mb-2">
            주제 탐색
          </h1>
          <p className="text-sm md:text-base text-muted-foreground">
            AI가 당신의 채널에 딱 맞는 주제를 찾았어요
          </p>
        </div>

        <div className="space-y-12">
          <section>
            <h2 className="text-xl font-semibold text-foreground mb-6">
              내 채널 강점 키우기
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {MOCK_GROWTH_TOPICS.map((topic) => (
                <TopicCard
                  key={topic.id}
                  id={topic.id}
                  badge={topic.badge}
                  title={topic.title}
                  description={topic.description}
                  hashtags={topic.hashtags}
                  onClick={() => handleTopicClick(topic)}
                />
              ))}
            </div>
          </section>

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
                  onClick={() => handleTopicClick(topic)}
                />
              ))}
            </div>
          </section>
        </div>
      </div>

      {selectedTopic && (
        <TopicDetailSidebar topic={selectedTopic} onClose={handleCloseDetail} />
      )}
    </div>
  )
}
