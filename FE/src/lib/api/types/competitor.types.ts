export interface CompetitorVideoIn {
    youtube_video_id: string;
    url: string;
    title: string;
    channel_title?: string;
    published_at?: string;
    duration_sec?: number;
    metrics_json?: Record<string, unknown>;
    caption_meta_json?: Record<string, unknown>;
    selection_json?: Record<string, unknown>;
}

export interface CompetitorSaveRequest {
    policy_json?: Record<string, unknown>;
    videos: CompetitorVideoIn[];
}

export interface CompetitorSaveResponse {
    collection_id: string;
    generated_at: string;
    video_count: number;
}
