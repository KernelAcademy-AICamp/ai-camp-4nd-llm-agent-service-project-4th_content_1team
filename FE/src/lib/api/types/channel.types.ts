export interface ChannelSearchRequest {
    query: string;
}

export interface ChannelSearchResult {
    channel_id: string;
    title: string;
    description?: string;
    thumbnail_url?: string;
    subscriber_count: number;
    view_count: number;
    video_count: number;
    custom_url?: string;
}

export interface ChannelSearchResponse {
    total_results: number;
    channels: ChannelSearchResult[];
}

export interface ChannelStatusResponse {
    has_channel: boolean;
    channel_id?: string;
    video_count: number;
    total_duration_minutes: number;
    has_enough_videos: boolean;
}
