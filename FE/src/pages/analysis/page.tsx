"use client"

import { useState } from "react"
import { DashboardSidebar } from "../dashboard/components/sidebar"
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs"
import { Input } from "../../components/ui/input"
import { Button } from "../../components/ui/button"
import { BarChart3, Users, Search, FileText } from "lucide-react"

export default function AnalysisPage() {
  const [searchQuery, setSearchQuery] = useState("")

  const handleSearch = () => {
    console.log("검색:", searchQuery)
    // TODO: 실제 검색 API 호출
  }

  return (
    <div className="min-h-screen bg-background flex">
      <DashboardSidebar />

      <main className="flex-1 p-6 overflow-auto">
        <div className="max-w-[1400px] mx-auto space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">채널 분석</h1>
            <p className="text-muted-foreground">
              내 채널과 경쟁 유튜버를 분석하고 최적의 콘텐츠 전략을 세우세요
            </p>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="competitor" className="w-full">
            <TabsList className="grid w-full grid-cols-4 mb-6">
              <TabsTrigger value="my-channel" className="gap-2">
                <BarChart3 className="w-4 h-4" />
                내 유튜브 분석
              </TabsTrigger>
              <TabsTrigger value="competitor" className="gap-2">
                <Users className="w-4 h-4" />
                경쟁 유튜버 분석
              </TabsTrigger>
              <TabsTrigger value="topics" className="gap-2">
                <FileText className="w-4 h-4" />
                주제 추천
              </TabsTrigger>
              <TabsTrigger value="trends" className="gap-2">
                <BarChart3 className="w-4 h-4" />
                실시간 트렌드
              </TabsTrigger>
            </TabsList>

            {/* 내 유튜브 분석 */}
            <TabsContent value="my-channel" className="space-y-6">
              <Card className="border-border/50 bg-card/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-lg">내 채널 통계</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    구현 예정: 구독자 추이, 조회수 분석, 인기 영상 등
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            {/* 경쟁 유튜버 분석 */}
            <TabsContent value="competitor" className="space-y-6">
              <Card className="border-border/50 bg-card/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-lg">경쟁 유튜버 추가</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                          placeholder="유튜버 이름 또는 채널 URL을 입력하세요"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleSearch()
                            }
                          }}
                          className="pl-10"
                        />
                      </div>
                      <Button 
                        onClick={handleSearch}
                        disabled={!searchQuery.trim()}
                        className="gap-2"
                      >
                        <Search className="w-4 h-4" />
                        검색
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      채널 이름, URL, 또는 @핸들을 입력하여 경쟁 유튜버를 추가하세요
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* 경쟁 유튜버 목록 (빈 상태) */}
              <Card className="border-border/50 bg-card/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-lg">등록된 경쟁 유튜버</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <Users className="w-12 h-12 text-muted-foreground mb-4" />
                    <h3 className="font-medium text-foreground mb-2">
                      아직 등록된 경쟁 유튜버가 없습니다
                    </h3>
                    <p className="text-sm text-muted-foreground max-w-[300px]">
                      위 검색창을 통해 경쟁 유튜버를 추가하고 채널을 비교 분석하세요
                    </p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* 주제 추천 */}
            <TabsContent value="topics" className="space-y-6">
              <Card className="border-border/50 bg-card/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-lg">AI 주제 추천</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    구현 예정: 트렌드 기반 주제 추천
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            {/* 실시간 트렌드 */}
            <TabsContent value="trends" className="space-y-6">
              <Card className="border-border/50 bg-card/50 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-lg">실시간 트렌드</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    구현 예정: 실시간 검색 트렌드, 급상승 키워드
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  )
}
