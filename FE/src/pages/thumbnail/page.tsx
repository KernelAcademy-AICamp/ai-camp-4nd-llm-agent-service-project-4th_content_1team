import { Suspense } from "react"
import { ThumbnailGenerator } from "./components/thumbnail-generator"
import { ThumbnailHeader } from "./components/thumbnail-header"

export default function ThumbnailPage() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Suspense fallback={<ThumbnailHeaderSkeleton />}>
        <ThumbnailHeader />
      </Suspense>
      <div className="flex-1 overflow-auto p-6">
        <ThumbnailGenerator />
      </div>
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
