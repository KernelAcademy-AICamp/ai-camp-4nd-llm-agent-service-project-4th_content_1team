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

export interface ReferenceArticle {
    title: string;
    summary: string;
    source: string;
    date?: string;  // optional - 백엔드에서 null일 수 있음
    url: string;
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
    error?: string;
}

export interface TaskStatusResponse {
    task_id: string;
    status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE';
    result?: ScriptGenResult;
}

// 스크립트 생성 시작
export const executeScriptGen = async (topic: string): Promise<TaskStatusResponse> => {
    const response = await api.post('/script-gen/execute', { topic });
    return response.data;
};

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
