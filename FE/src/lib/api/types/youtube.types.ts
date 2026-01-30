// YouTube 관련 타입 정의

export interface VideoSearchRequest {
    keywords: string;
    title?: string;
    max_results?: number;
}

export interface VideoStatistics {
    view_count: number;
    like_count: number;
    comment_count: number;
}

export interface VideoItem {
    video_id: string;
    title: string;
    description: string;
    thumbnail_url: string;
    channel_id: string;
    channel_title: string;
    published_at: string;
    statistics: VideoStatistics;
    popularity_score: number;
    days_since_upload: number;
    has_caption: boolean;
}

export interface VideoSearchResponse {
    total_results: number;
    query: string;
    videos: VideoItem[];
}
