import { api } from '../client';
import type { ChannelSearchRequest, ChannelSearchResponse } from '../types/channel.types';

export const searchChannels = async (query: string): Promise<ChannelSearchResponse> => {
    const response = await api.post('/api/v1/channels/search', { query });
    return response.data;
};
