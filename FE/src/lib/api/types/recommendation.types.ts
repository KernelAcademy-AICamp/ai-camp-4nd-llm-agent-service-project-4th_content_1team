// 주제 기본 정보
export interface TopicBase {
    title: string;
    based_on_topic: string | null;
    trend_basis: string | null;
    recommendation_reason: string | null;
    urgency: 'urgent' | 'normal' | 'evergreen';
    search_keywords: string[];  // ["키워드1", "키워드2", ...]
    content_angles: string[];
    thumbnail_idea: string | null;
}

// 주제 응답 (조회용)
export interface TopicResponse extends TopicBase {
    id: string;
    channel_id: string;
    rank: number;
    display_status: 'shown' | 'queued' | 'skipped';
    status: 'recommended' | 'confirmed' | 'scripting' | 'completed';
    scheduled_date: string | null;
    created_at: string | null;
    expires_at: string | null;
    confirmed_at: string | null;
    topic_type: 'channel' | 'trend';
}

// 전체 주제 목록 응답
export interface TopicsListResponse {
    channel_topics: TopicResponse[];  // shown 상태 (최대 5개)
    trend_topics: TopicResponse[];    // shown 상태 (최대 2개)
    channel_expires_at: string | null;
    trend_expires_at: string | null;
}

// 추천 상태 확인 응답
export interface TopicsStatusResponse {
    channel_exists: boolean;
    channel_expired: boolean;
    trend_exists: boolean;
    trend_expired: boolean;
}

// 주제 상태 변경 요청
export interface TopicStatusUpdate {
    status: 'confirmed' | 'scripting' | 'completed';
    scheduled_date?: string;
}

// 주제 건너뛰기 응답
export interface TopicSkipResponse {
    skipped_topic_id: string;
    new_topic: TopicResponse | null;
    remaining_queued: number;
}

// 트렌드 추천 생성 응답
export interface TrendTopicsGenerateResponse {
    success: boolean;
    message: string;
    generated_count: number;
    shown_count: number;
    topics: TopicResponse[];
}
