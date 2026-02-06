import { api } from '../client';
import type {
    CompetitorChannelCreate,
    CompetitorChannelResponse,
    CompetitorChannelListResponse,
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
