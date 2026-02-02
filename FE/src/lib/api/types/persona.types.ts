// 페르소나 응답 타입
export interface PersonaResponse {
    id: string;
    channel_id: string;

    // 종합 서술
    persona_summary?: string;

    // 정체성
    one_liner?: string;
    main_topics?: string[];
    content_style?: string;
    differentiator?: string;

    // 타겟 시청자
    target_audience?: string;
    audience_needs?: string;

    // 성공 공식
    hit_topics?: string[];
    title_patterns?: string[];
    optimal_duration?: string;

    // 성장 기회
    growth_opportunities?: string[];

    // 근거
    evidence?: any[];

    // 카테고리 (분석 결과 + 사용자 선택)
    analyzed_categories?: string[];
    analyzed_subcategories?: string[];
    preferred_categories?: string[];
    preferred_subcategories?: string[];

    // 매칭용 키워드
    topic_keywords?: string[];
    style_keywords?: string[];

    // 메타
    created_at?: string;
    updated_at?: string;
}

// 페르소나 생성 응답
export interface PersonaGenerateResponse {
    success: boolean;
    message: string;
    persona?: PersonaResponse;
}

// 페르소나 수정 요청
export interface PersonaUpdateRequest {
    persona_summary?: string;
    one_liner?: string;
    main_topics?: string[];
    content_style?: string;
    differentiator?: string;
    target_audience?: string;
    audience_needs?: string;
    hit_topics?: string[];
    title_patterns?: string[];
    optimal_duration?: string;
    growth_opportunities?: string[];
    topic_keywords?: string[];
    style_keywords?: string[];
    preferred_categories?: string[];
    preferred_subcategories?: string[];
}
