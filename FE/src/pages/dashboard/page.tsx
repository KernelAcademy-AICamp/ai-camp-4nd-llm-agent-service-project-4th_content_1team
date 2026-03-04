"use client"

import { useState } from "react"
import { ContentCalendar } from "./components/calendar"
import { UploadSettings } from "./components/upload-settings"
import { ConfirmedTopicsPanel } from "./components/confirmed-topics-panel"
import { RecommendationCards } from "./components/recommendation-cards"
import type { TopicResponse } from "../../lib/api/types"

interface ContentTopic {
  id: string
  title: string
  reason: string
  type: string
  date: string  // "2024-02-15" 형식
  week?: number  // 레거시 호환
  confirmed?: boolean
  // API 추천 데이터 추가 필드
  based_on_topic?: string
  trend_basis?: string
  recommendation_reason?: string
  content_angles?: string[]
  thumbnail_idea?: string
  urgency?: string
  search_keywords?: string[]
  topic_type?: 'channel' | 'trend'
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
  // 추천 → 캘린더 추가
  const handleAddToCalendar = (topic: TopicResponse, date: string) => {
    const newTopic: ContentTopic = {
      id: topic.id,
      title: topic.title,
      reason: topic.recommendation_reason || topic.trend_basis || "",
      type: urgencyToType[topic.urgency] || "trend",
      date: date,
      confirmed: true,  // 날짜 지정 = 확정
      // 추가 정보 보존
      based_on_topic: topic.based_on_topic || undefined,
      trend_basis: topic.trend_basis || undefined,
      recommendation_reason: topic.recommendation_reason || undefined,
      content_angles: topic.content_angles,
      thumbnail_idea: topic.thumbnail_idea || undefined,
      urgency: topic.urgency,
      search_keywords: topic.search_keywords,
      topic_type: topic.topic_type,
    }

    setCalendarTopics(prev => [...prev, newTopic])
    // 확정된 주제 패널에도 추가
    setConfirmedTopics(prev => [...prev, newTopic])
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
