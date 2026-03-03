import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Plus, FileText, Loader2, ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "../../components/ui/button"
import { ScriptCard } from "./components/script-card"
import { getScriptList, type ScriptListItem, type PaginationInfo } from "../../lib/api/services"

export default function ScriptListPage() {
  const navigate = useNavigate()
  const [scripts, setScripts] = useState<ScriptListItem[]>([])
  const [pagination, setPagination] = useState<PaginationInfo | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const PAGE_SIZE = 8

  // 스크립트 목록 조회
  useEffect(() => {
    const fetchScripts = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const response = await getScriptList(currentPage, PAGE_SIZE)
        setScripts(response.scripts)
        setPagination(response.pagination)
      } catch (err: any) {
        console.error("스크립트 목록 조회 실패:", err)
        setError("스크립트 목록을 불러오는데 실패했습니다.")
      } finally {
        setIsLoading(false)
      }
    }
    fetchScripts()
  }, [currentPage])

  // 새 스크립트 생성 핸들러
  const handleCreateScript = () => {
    navigate("/script/edit")
  }

  // 스크립트 카드 클릭 핸들러
  const handleScriptClick = (script: ScriptListItem) => {
    navigate(`/script/edit?topicId=${script.topic_request_id}`)
  }

  // 페이지 변경 핸들러
  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  return (
    <div className="min-h-full w-full bg-background px-4 py-6 md:p-6">
      <div className="w-full mx-0 md:max-w-[1001px] lg:max-w-[1340px] md:mx-auto">
        {/* 헤더 */}
        <div className="mb-8 md:mb-10">
          <div className="mb-4 md:mb-6">
            <h1 className="text-2xl md:text-3xl font-semibold text-foreground mb-2">
              스크립트
            </h1>
            <p className="text-sm md:text-base text-muted-foreground">
              오늘은 어떤 스크립트를 생성해 볼까요?
            </p>
          </div>

          {/* 새 스크립트 버튼 + 페이지네이션 */}
          <div className="flex items-center justify-between">
            <Button 
              onClick={handleCreateScript}
              className="bg-[#09090b] hover:bg-[#1a1a1f]"
            >
              <Plus className="w-5 h-5" />
              새 스크립트
            </Button>

            {/* 페이지네이션 */}
            {pagination && pagination.total_pages > 1 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage <= 1}
                  className="h-8 w-8 p-0"
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm text-muted-foreground px-2">
                  {currentPage} / {pagination.total_pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage >= pagination.total_pages}
                  className="h-8 w-8 p-0"
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* 로딩 상태 */}
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
            <span className="ml-3 text-muted-foreground">스크립트 목록을 불러오고 있어요...</span>
          </div>
        )}

        {/* 에러 상태 */}
        {!isLoading && error && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button variant="outline" onClick={() => setCurrentPage(1)}>
              다시 시도
            </Button>
          </div>
        )}

        {/* 빈 상태 */}
        {!isLoading && !error && scripts.length === 0 && (
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
        )}

        {/* 스크립트 목록 */}
        {!isLoading && !error && scripts.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 justify-items-stretch md:justify-items-start">
            {scripts.map((script) => (
              <ScriptCard
                key={script.id}
                id={script.id}
                title={script.title}
                created_at={script.created_at || ""}
                thumbnail={script.thumbnail || undefined}
                is_completed={script.is_completed}
                onClick={() => handleScriptClick(script)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
