

import { Suspense } from "react"
import { ThumbnailGenerator } from "./components/thumbnail-generator"
import { ThumbnailHeader } from "./components/thumbnail-header"

export default function ThumbnailPage() {
  return (
    <div className="min-h-screen bg-background flex">
      <main className="flex-1 flex flex-col overflow-hidden">
        <Suspense fallback={<ThumbnailHeaderSkeleton />}>
          <ThumbnailHeader />
        </Suspense>

        <div className="flex-1 overflow-auto p-6">
          <ThumbnailGenerator />
        </div>
      </main>
    </div>
  )
}

function ThumbnailHeaderSkeleton() {
  return (
    <div className="border-b border-border p-4">
      <div className="h-8 w-64 bg-muted animate-pulse rounded" />
    </div>
  )
}
