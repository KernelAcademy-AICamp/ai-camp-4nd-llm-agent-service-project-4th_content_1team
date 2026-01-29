import { api } from '../client';
import type { CompetitorSaveRequest, CompetitorSaveResponse } from '../types';

export const saveCompetitorVideos = async (
    request: CompetitorSaveRequest
): Promise<CompetitorSaveResponse> => {
    const response = await api.post('/api/v1/competitor/save', request);
    return response.data;
};
