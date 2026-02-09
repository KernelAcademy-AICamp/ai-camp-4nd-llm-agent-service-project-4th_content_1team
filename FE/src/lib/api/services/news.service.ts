import { api } from '../client';
import type { NewsSearchRequest, NewsSearchResponse } from '../types/news.types';

export const searchNews = async (request: NewsSearchRequest): Promise<NewsSearchResponse> => {
    const response = await api.post('/api/v1/news/search', request);
    return response.data;
};
