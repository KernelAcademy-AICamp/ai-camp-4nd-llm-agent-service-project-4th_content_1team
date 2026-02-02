import { api } from '../client';
import type {
    RecommendationResponse,
    RecommendationGenerateResponse,
    RecommendationStatusResponse,
} from '../types/recommendation.types';

// 추천 조회
export const getRecommendations = async (): Promise<RecommendationResponse> => {
    const response = await api.get('/recommendations');
    return response.data;
};

// 추천 생성
export const generateRecommendations = async (): Promise<RecommendationGenerateResponse> => {
    const response = await api.post('/recommendations/generate');
    return response.data;
};

// 추천 상태 확인
export const getRecommendationStatus = async (): Promise<RecommendationStatusResponse> => {
    const response = await api.get('/recommendations/status');
    return response.data;
};
