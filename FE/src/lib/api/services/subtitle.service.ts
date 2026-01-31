import { api } from '../client';
import type { SubtitleFetchRequest, SubtitleFetchResponse } from '../types';

export const fetchSubtitles = async (
    request: SubtitleFetchRequest
): Promise<SubtitleFetchResponse> => {
    const response = await api.post('/api/v1/subtitle/fetch', request);
    return response.data;
};
