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
