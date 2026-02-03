import { api } from '../client';
import type {
    TopicsListResponse,
    TopicsStatusResponse,
    TopicSkipResponse,
    TrendTopicsGenerateResponse,
    TopicStatusUpdate,
    TopicResponse,
} from '../types/recommendation.types';

// 전체 추천 주제 조회 (채널 맞춤 + 트렌드)
export const getTopics = async (): Promise<TopicsListResponse> => {
    const response = await api.get('/recommendations/topics');
    return response.data;
};

// 추천 상태 확인
export const getTopicsStatus = async (): Promise<TopicsStatusResponse> => {
    const response = await api.get('/recommendations/topics/status');
    return response.data;
};

// 트렌드 추천 생성
export const generateTrendTopics = async (): Promise<TrendTopicsGenerateResponse> => {
    const response = await api.post('/recommendations/topics/trend/generate');
    return response.data;
};

// 주제 건너뛰기 (개별 새로고침)
export const skipTopic = async (
    topicType: 'channel' | 'trend',
    topicId: string
): Promise<TopicSkipResponse> => {
    const response = await api.post(`/recommendations/topics/${topicType}/${topicId}/skip`);
    return response.data;
};

// 주제 상태 변경
export const updateTopicStatus = async (
    topicType: 'channel' | 'trend',
    topicId: string,
    update: TopicStatusUpdate
): Promise<TopicResponse> => {
    const response = await api.patch(
        `/recommendations/topics/${topicType}/${topicId}/status`,
        update
    );
    return response.data;
};
