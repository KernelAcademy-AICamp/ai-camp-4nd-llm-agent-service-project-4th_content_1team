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
        key_points?: string[]; // 핵심 포인트 (article_analyzer 추출)
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

// 작업 상태 조회
export const checkScriptGenStatus = async (taskId: string): Promise<TaskStatusResponse> => {
    const response = await api.get(`/script-gen/status/${taskId}`);
    return response.data;
};

// 폴링 헬퍼 (완료될 때까지 대기)
// 첫 시도 실패 완화: Celery worker cold start를 위해 최초 2초 대기 후 폴링 시작
export const pollScriptGenResult = async (
    taskId: string,
    onStatusChange?: (status: string) => void
): Promise<ScriptGenResult> => {
    await new Promise((r) => setTimeout(r, 2000));
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
                    reject(new Error(statusData.result?.error || statusData.result?.message || 'Task Failed'));
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
