import { api } from '../client';
import type { ChannelSearchRequest, ChannelSearchResponse, ChannelStatusResponse } from '../types/channel.types';

export const searchChannels = async (query: string): Promise<ChannelSearchResponse> => {
    const response = await api.post('/api/v1/channels/search', { query });
    return response.data;
};

// 채널 상태 확인 (온보딩 분기 판단용)
export const getChannelStatus = async (): Promise<ChannelStatusResponse> => {
    const response = await api.get('/api/v1/channels/me/status');
    return response.data;
};
