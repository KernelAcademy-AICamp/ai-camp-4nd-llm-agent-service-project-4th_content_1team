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

export interface CompetitorChannelVideo {
    id: string;
    video_id: string;
    title: string;
    description?: string;
    thumbnail_url?: string;
    published_at?: string;
    duration?: string;
    view_count: number;
    like_count: number;
    comment_count: number;
    
    // AI 분석
    analysis_summary?: string;
    analysis_strengths?: string[];
    analysis_weaknesses?: string[];
    audience_reaction?: string;
    applicable_points?: string[];
    comment_insights?: {
        reactions: string[];
        needs: string[];
    };
    analyzed_at?: string;
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
    recent_videos?: CompetitorChannelVideo[];  // relationship
    created_at: string;
    updated_at: string;
    analyzed_at?: string;
}

export interface CompetitorChannelListResponse {
    total: number;
    channels: CompetitorChannelResponse[];
}

export interface CommentInsights {
    reactions: string[];
    needs: string[];
}

export interface RecentVideoAnalyzeResponse {
    video_id: string;
    analysis_strengths: string[];
    analysis_weaknesses: string[];
    applicable_points: string[];
    comment_insights: CommentInsights;
    analyzed_at: string;
}
