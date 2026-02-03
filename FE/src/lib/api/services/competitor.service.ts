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
