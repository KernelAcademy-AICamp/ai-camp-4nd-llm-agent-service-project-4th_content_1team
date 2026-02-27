import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Plus, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScriptCard } from "./components/script-card"

interface Script {
  id: string
  title: string
  created_at: string
  thumbnail?: string
  is_completed?: boolean
}

const MOCK_SCRIPTS: Script[] = [
  {
    id: "1",
    title: "미국 의대생 브이로그: 외과 실습 돌다 허리가 나갈 뻔한 미국 의대생 ㅣ 고단뻔한 미국 의대생 ㅣ 고단뻔한 미국 의대생 ㅣ 고단",
    created_at: "2026-01-13T10:30:00",
    thumbnail: "/images/placeholder-thumbnail.png",
    is_completed: false,
  },
  {
    id: "2",
    title: "AI 기술 트렌드 2026: 생성형 AI의 미래와 활용 방안",
    created_at: "2026-01-12T15:20:00",
    is_completed: false,
  },
  {
    id: "3",
    title: "프로그래밍 초보자를 위한 Python 완벽 가이드",
    created_at: "2026-01-11T09:15:00",
    is_completed: true,
  },
  {
    id: "4",
    title: "유튜브 채널 성장 전략: 구독자 1만명 달성 노하우",
    created_at: "2026-01-10T14:45:00",
    is_completed: false,
  },
  {
    id: "5",
    title: "효율적인 시간 관리 방법: 생산성을 높이는 10가지 팁",
    created_at: "2026-01-09T11:00:00",
    is_completed: false,
  },
  {
    id: "6",
    title: "건강한 식습관 만들기: 영양 균형 잡힌 식단 구성법",
    created_at: "2026-01-08T16:30:00",
    is_completed: true,
  },
  {
    id: "7",
    title: "운동 루틴 설계: 초보자를 위한 홈트레이닝 가이드",
    created_at: "2026-01-07T08:20:00",
    is_completed: false,
  },
  {
    id: "8",
    title: "재테크 시작하기: 20대를 위한 투자 입문 가이드",
    created_at: "2026-01-06T13:40:00",
    is_completed: false,
  },
]

export default function ScriptListPage() {
  const navigate = useNavigate()
  const [scripts] = useState<Script[]>(MOCK_SCRIPTS)

  const handleCreateScript = () => {
    navigate("/script/edit")
  }

  const handleScriptClick = (scriptId: string) => {
    navigate(`/script/edit?topicId=${scriptId}`)
  }

  return (
    <div className="min-h-full w-full bg-background px-4 py-6 md:p-6">
      <div className="w-full mx-0 md:max-w-[1001px] lg:max-w-[1340px] md:mx-auto">
        <div className="mb-8 md:mb-10">
          <div className="mb-4 md:mb-6">
            <h1 className="text-2xl md:text-3xl font-semibold text-foreground mb-2">
              스크립트
            </h1>
            <p className="text-sm md:text-base text-muted-foreground">
              오늘은 어떤 스크립트를 생성해 볼까요?
            </p>
          </div>
          <Button
            onClick={handleCreateScript}
            className="bg-[#09090b] hover:bg-[#1a1a1f] w-full md:w-auto"
          >
            <Plus className="w-5 h-5" />
            새 스크립트
          </Button>
        </div>

        {scripts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <FileText className="w-16 h-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">
              아직 생성된 스크립트가 없습니다
            </h3>
            <p className="text-sm text-muted-foreground mb-6 max-w-[300px]">
              새 스크립트 버튼을 눌러 첫 스크립트를 생성해보세요
            </p>
            <Button onClick={handleCreateScript}>
              <Plus className="w-4 h-4" />
              첫 스크립트 만들기
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 justify-items-stretch md:justify-items-start">
            {scripts.map((script) => (
              <ScriptCard
                key={script.id}
                id={script.id}
                title={script.title}
                created_at={script.created_at}
                thumbnail={script.thumbnail}
                is_completed={script.is_completed}
                onClick={() => handleScriptClick(script.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
