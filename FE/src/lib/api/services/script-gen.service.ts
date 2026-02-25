import { api } from '../client';

// 타입 정의
export interface ScriptChapter {
    title: string;
    content: string;
}

export interface GeneratedScript {
    hook: string;
    chapters: ScriptChapter[];
    outro: string;
}

export interface Citation {
    marker: string;
    number: number;
    fact_id: string;
    content: string;
    category: string;
    source: string;
    source_title: string;
    source_url: string;
}

export interface ReferenceArticle {
    title: string;
    summary: string;
    source: string;
    date?: string;  // optional - 백엔드에서 null일 수 있음
    url: string;
    query?: string; // 검색에 사용된 키워드
    analysis?: {
        facts: string[];
        opinions: string[];
    };
    images?: Array<{
        url: string;
        caption?: string;
        is_chart?: boolean;
    }>;
}

export interface ScriptGenResult {
    success: boolean;
    message: string;
    script?: GeneratedScript;
    references?: ReferenceArticle[];
    competitor_videos?: any[];
    citations?: Citation[];
    error?: string;
    topic_request_id?: string;
}

export interface TaskStatusResponse {
    task_id: string;
    status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE';
    result?: ScriptGenResult;
}

// 스크립트 생성 시작
export const executeScriptGen = async (
    topic: string,
    topicRecommendationId?: string,
): Promise<TaskStatusResponse> => {
    const response = await api.post('/script-gen/execute', {
        topic,
        topic_recommendation_id: topicRecommendationId,
    });
    return response.data;
};

export interface YoutubeVideo {
    video_id: string;
    title: string;
    channel: string;
    url: string;
    thumbnail: string;
    view_count: number;
    view_velocity: number;
    search_keyword: string;
    published_at?: string;
}

// 작업 상태 조회
export const checkScriptGenStatus = async (taskId: string): Promise<TaskStatusResponse> => {
    const response = await api.get(`/script-gen/status/${taskId}`);
    return response.data;
};

// 폴링 헬퍼 (완료될 때까지 대기)
export const pollScriptGenResult = async (
    taskId: string,
    onStatusChange?: (status: string) => void
): Promise<ScriptGenResult> => {
    return new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
            try {
                const statusData = await checkScriptGenStatus(taskId);
                if (onStatusChange) onStatusChange(statusData.status);

                if (statusData.status === 'SUCCESS' && statusData.result) {
                    clearInterval(interval);
                    resolve(statusData.result);
                } else if (statusData.status === 'FAILURE') {
                    clearInterval(interval);
                    reject(new Error(statusData.result?.error || 'Task Failed'));
                }
            } catch (error) {
                clearInterval(interval);
                reject(error);
            }
        }, 3000);
    });
};

// 스크립트 생성 이력 조회 (새로고침 후 결과 복원)
export interface ScriptHistoryItem {
    topic_request_id: string;
    topic_title: string;
    status: string;
    created_at: string | null;
    script: GeneratedScript | null;
    references: ReferenceArticle[] | null;
    competitor_videos: any[] | null;
    citations: Citation[] | null;
}

export const getScriptHistory = async (limit: number = 10): Promise<ScriptHistoryItem[]> => {
    const response = await api.get(`/script-gen/scripts/history?limit=${limit}`);
    return response.data.results || [];
};

// 특정 topic_request_id로 스크립트 결과 조회
export const getScriptById = async (topicRequestId: string): Promise<ScriptHistoryItem> => {
    const response = await api.get(`/script-gen/scripts/${topicRequestId}`);
    return response.data;
};

// 참고 영상 상세 분석 (자막+댓글 → 장단점, 시청자 반응, 적용 포인트)
export interface ReferenceVideoAnalyzeResult {
    video_id: string;
    analysis_strengths: string[];
    analysis_weaknesses: string[];
    applicable_points: string[];
    comment_insights: { reactions: string[]; needs: string[] };
    analyzed_at: string;
}
export const analyzeReferenceVideo = async (
    youtubeVideoId: string,
    title: string = '',
): Promise<ReferenceVideoAnalyzeResult> => {
    const response = await api.post('/script-gen/analyze-reference-video', {
        youtube_video_id: youtubeVideoId,
        title: title || '제목 없음',
    });
    return response.data;
};

