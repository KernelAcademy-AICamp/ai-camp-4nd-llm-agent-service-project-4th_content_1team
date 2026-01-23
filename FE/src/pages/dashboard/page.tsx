"use client"

import { useState } from "react"
import { DashboardSidebar } from "./components/sidebar"
import { ContentCalendar } from "./components/calendar"
import { TrendPanel } from "./components/trend-panel"
import { UploadSettings } from "./components/upload-settings"
import { ConfirmedTopicsPanel } from "./components/confirmed-topics-panel"

interface ContentTopic {
  id: number
  title: string
  reason: string
  type: string
  week: number
  confirmed?: boolean
}

export default function DashboardPage() {
  const [weeklyUploads, setWeeklyUploads] = useState(2)
  const [confirmedTopics, setConfirmedTopics] = useState<ContentTopic[]>([])

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

          {/* Main Grid - Calendar + Insights side by side, Trend below */}
          <div className="flex flex-col gap-6">
            {/* Top Row: Calendar + Confirmed Topics */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
              {/* Calendar */}
              <div className="xl:col-span-7">
                <ContentCalendar
                  weeklyUploads={weeklyUploads}
                  onTopicConfirm={handleTopicConfirm}
                  confirmedTopics={confirmedTopics}
                />
              </div>

              {/* Confirmed Topics Panel - Directly right of calendar */}
              <div className="xl:col-span-5">
                <ConfirmedTopicsPanel confirmedTopics={confirmedTopics} />
              </div>
            </div>

            {/* Bottom Row: Trend Panel */}
            <div>
              <TrendPanel />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
