"use client"

import { Suspense } from "react"
import { UploadForm } from "./components/upload-form"
import { UploadHeader } from "./components/upload-header"

export default function UploadPage() {
  return (
    <div className="min-h-screen bg-background flex">
      <main className="flex-1 flex flex-col overflow-hidden">
        <Suspense fallback={<UploadHeaderSkeleton />}>
          <UploadHeader />
        </Suspense>

        <div className="flex-1 overflow-auto p-6">
          <UploadForm />
        </div>
      </main>
    </div>
  )
}

function UploadHeaderSkeleton() {
  return (
    <div className="border-b border-border p-4">
      <div className="h-8 w-64 bg-muted animate-pulse rounded" />
    </div>
  )
}
