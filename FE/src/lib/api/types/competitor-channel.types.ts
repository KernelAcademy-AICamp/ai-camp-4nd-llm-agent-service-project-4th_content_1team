export interface CompetitorChannelCreate {
    channel_id: string;
    title: string;
    description?: string;
    custom_url?: string;
    thumbnail_url?: string;
    subscriber_count: number;
    view_count: number;
    video_count: number;
    topic_categories?: string[];
    keywords?: string;
    country?: string;
    published_at?: string;
    raw_data?: Record<string, unknown>;
}

export interface CompetitorChannelResponse {
    id: string;
    channel_id: string;
    title: string;
    description?: string;
    custom_url?: string;
    thumbnail_url?: string;
    subscriber_count: number;
    view_count: number;
    video_count: number;
    strengths?: string[];
    channel_personality?: string;
    target_audience?: string;
    content_style?: string;
    created_at: string;
    updated_at: string;
    analyzed_at?: string;
}

export interface CompetitorChannelListResponse {
    total: number;
    channels: CompetitorChannelResponse[];
}
