import { api } from '../client';
import type {
    CompetitorSaveRequest,
    CompetitorSaveResponse,
    VideoAnalyzeResponse,
} from '../types';

export const saveCompetitorVideos = async (
    request: CompetitorSaveRequest
): Promise<CompetitorSaveResponse> => {
    const response = await api.post('/api/v1/competitor/save', request);
    return response.data;
};

export const analyzeVideoContent = async (
    youtubeVideoId: string
): Promise<VideoAnalyzeResponse> => {
    const response = await api.post('/api/v1/competitor/analyze', {
        youtube_video_id: youtubeVideoId,
    });
    return response.data;
};

export interface BatchAnalyzeResponse {
    total: number;
    processed: number;
    skipped: number;
    failed: number;
}

export const batchAnalyzeVideos = async (
    youtubeVideoIds: string[]
): Promise<BatchAnalyzeResponse> => {
    const response = await api.post('/api/v1/competitor/analyze/batch', {
        youtube_video_ids: youtubeVideoIds,
    });
    return response.data;
};
