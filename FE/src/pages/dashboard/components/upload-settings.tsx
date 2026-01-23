"use client"

import { Button } from "../../../components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../../../components/ui/popover"
import { Slider } from "../../../components/ui/slider"
import { Settings, Upload } from "lucide-react"

interface UploadSettingsProps {
  weeklyUploads: number
  onUploadChange: (value: number) => void
}

export function UploadSettings({ weeklyUploads, onUploadChange }: UploadSettingsProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" className="gap-2 bg-transparent">
          <Upload className="w-4 h-4" />
          주 {weeklyUploads}회 업로드
          <Settings className="w-4 h-4 text-muted-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80" align="end">
        <div className="space-y-4">
          <div className="space-y-2">
            <h4 className="font-medium">주간 업로드 횟수</h4>
            <p className="text-sm text-muted-foreground">
              업로드 횟수에 따라 추천 콘텐츠 개수가 조절됩니다.
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-3xl font-bold text-primary">{weeklyUploads}</span>
              <span className="text-muted-foreground">회 / 주</span>
            </div>
            <Slider
              value={[weeklyUploads]}
              onValueChange={(value) => onUploadChange(value[0])}
              max={7}
              min={1}
              step={1}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1회</span>
              <span>7회</span>
            </div>
          </div>

          <div className="pt-2 border-t border-border">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">월간 콘텐츠 추천</span>
              <span className="font-semibold text-primary">{weeklyUploads * 4}개</span>
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
