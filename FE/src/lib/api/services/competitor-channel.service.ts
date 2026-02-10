import { api } from '../client';
import type {
    CompetitorChannelCreate,
    CompetitorChannelResponse,
    CompetitorChannelListResponse,
    RecentVideoAnalyzeResponse,
    CompetitorTopicsGenerateResponse,
    AutoAnalyzeResponse,
} from '../types/competitor-channel.types';

export const addCompetitorChannel = async (
    data: CompetitorChannelCreate
): Promise<CompetitorChannelResponse> => {
    const response = await api.post('/api/v1/channels/competitor/add', data);
    return response.data;
};

export const getCompetitorChannels = async (): Promise<CompetitorChannelListResponse> => {
    const response = await api.get('/api/v1/channels/competitor/list');
    return response.data;
};

export const deleteCompetitorChannel = async (competitorId: string): Promise<void> => {
    await api.delete(`/api/v1/channels/competitor/${competitorId}`);
};

export interface FetchSubtitlesResponse {
    success: boolean;
    message: string;
    data: {
        video_id: string;
        status: string;
        source: string;
        tracks: Array<{
            language_code: string;
            language_name: string;
            is_auto_generated: boolean;
            cues: Array<{
                start: number;
                end: number;
                text: string;
            }>;
        }>;
        no_captions: boolean;
        error?: string;
    } | null;
}

export const fetchVideoSubtitles = async (videoId: string): Promise<FetchSubtitlesResponse> => {
    const response = await api.post('/api/v1/channels/competitor/fetch-subtitles', {
        video_id: videoId
    });
    return response.data;
};

export const refreshCompetitorVideos = async (): Promise<{
    success: boolean;
    updated_channels: number;
    total_channels: number;
}> => {
    const response = await api.post('/api/v1/channels/competitor/refresh-videos');
    return response.data;
};

export const analyzeRecentVideo = async (videoId: string): Promise<RecentVideoAnalyzeResponse> => {
    const response = await api.post('/api/v1/channels/competitor/analyze-video', {
        video_id: videoId
    });
    return response.data;
};

export const generateCompetitorTopics = async (): Promise<CompetitorTopicsGenerateResponse> => {
    const response = await api.post('/api/v1/channels/competitor/generate-topics');
    return response.data;
};

export const autoAnalyzeCompetitors = async (): Promise<AutoAnalyzeResponse> => {
    const response = await api.post('/api/v1/channels/competitor/auto-analyze', null, {
        timeout: 300000, // 5분 타임아웃 (여러 영상 분석)
    });
    return response.data;
};
