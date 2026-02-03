"use client"

import { useState } from "react"
import { DashboardSidebar } from "./components/sidebar"
import { ContentCalendar } from "./components/calendar"
import { UploadSettings } from "./components/upload-settings"
import { ConfirmedTopicsPanel } from "./components/confirmed-topics-panel"
import { RecommendationCards } from "./components/recommendation-cards"
import type { RecommendationItem } from "../../lib/api/types"

interface ContentTopic {
  id: number
  title: string
  reason: string
  type: string
  week: number
  confirmed?: boolean
  // API 추천 데이터 추가 필드
  based_on_topic?: string
  trend_basis?: string
  recommendation_reason?: string
  content_angles?: string[]
  thumbnail_idea?: string
  urgency?: string
}

// urgency를 type으로 매핑
const urgencyToType: Record<string, string> = {
  urgent: "hot",
  normal: "trend",
  evergreen: "evergreen",
}

export default function DashboardPage() {
  const [weeklyUploads, setWeeklyUploads] = useState(2)
  const [confirmedTopics, setConfirmedTopics] = useState<ContentTopic[]>([])
  const [calendarTopics, setCalendarTopics] = useState<ContentTopic[]>([])
  const [nextId, setNextId] = useState(1000) // API 추천 주제용 ID

  // 추천 → 캘린더 추가
  const handleAddToCalendar = (recommendation: RecommendationItem, week: number) => {
    const newTopic: ContentTopic = {
      id: nextId,
      title: recommendation.title,
      reason: recommendation.recommendation_reason || recommendation.trend_basis,
      type: urgencyToType[recommendation.urgency] || "trend",
      week: week,
      confirmed: false,
      // 추가 정보 보존
      based_on_topic: recommendation.based_on_topic,
      trend_basis: recommendation.trend_basis,
      recommendation_reason: recommendation.recommendation_reason,
      content_angles: recommendation.content_angles,
      thumbnail_idea: recommendation.thumbnail_idea,
      urgency: recommendation.urgency,
    }

    setCalendarTopics(prev => [...prev, newTopic])
    setNextId(prev => prev + 1)
  }

  // 캘린더에서 주제 확정
  const handleTopicConfirm = (topic: ContentTopic) => {
    setConfirmedTopics(prev => {
      const exists = prev.some(t => t.id === topic.id)
      if (exists) return prev
      return [...prev, topic]
    })
  }

  return (
    <div className="min-h-screen bg-background flex">
      <DashboardSidebar />

      <main className="flex-1 p-6 overflow-auto">
        <div className="max-w-[1600px] mx-auto space-y-6">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-foreground">콘텐츠 대시보드</h1>
              <p className="text-muted-foreground">2026년 1월 콘텐츠 계획을 관리하세요</p>
            </div>
            <UploadSettings
              weeklyUploads={weeklyUploads}
              onUploadChange={setWeeklyUploads}
            />
          </div>

          {/* AI 추천 주제 (상단) */}
          <RecommendationCards onAddToCalendar={handleAddToCalendar} />

          {/* Calendar + Confirmed Topics */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
            {/* Calendar */}
            <div className="xl:col-span-7">
              <ContentCalendar
                weeklyUploads={weeklyUploads}
                onTopicConfirm={handleTopicConfirm}
                confirmedTopics={confirmedTopics}
                externalTopics={calendarTopics}
              />
            </div>

            {/* Confirmed Topics Panel */}
            <div className="xl:col-span-5">
              <ConfirmedTopicsPanel confirmedTopics={confirmedTopics} />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
