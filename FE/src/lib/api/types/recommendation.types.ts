// 검색 키워드 (스크립트 작성용)
export interface SearchKeywords {
    youtube_main: string[];        // 메인 영상 검색용
    youtube_reference: string[];   // 참고 영상 검색용
    google_news: string[];         // 최신 뉴스/기사 검색용
    google_research: string[];     // 심층 자료 검색용
}

// 개별 추천 항목
export interface RecommendationItem {
    title: string;
    based_on_topic: string;
    trend_basis: string;
    recommendation_reason?: string;
    search_keywords?: SearchKeywords;
    content_angles: string[];
    thumbnail_idea?: string;
    urgency: 'urgent' | 'normal' | 'evergreen';
}

// 추천 조회 응답
export interface RecommendationResponse {
    channel_id: string;
    recommendations: RecommendationItem[];
    generated_at: string;
    expires_at: string;
    is_expired: boolean;
}

// 추천 생성 응답
export interface RecommendationGenerateResponse {
    success: boolean;
    message: string;
    data?: RecommendationResponse;
}

// 추천 상태 응답
export interface RecommendationStatusResponse {
    exists: boolean;
    is_expired: boolean | null;
    generated_at: string | null;
    expires_at: string | null;
}
