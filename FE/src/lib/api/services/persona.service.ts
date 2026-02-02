import { api } from '../client';
import type { PersonaResponse, PersonaGenerateResponse, PersonaUpdateRequest } from '../types';

// 내 페르소나 조회
export const getMyPersona = async (): Promise<PersonaResponse> => {
    const response = await api.get('/personas/me');
    return response.data;
};

// 페르소나 생성 (채널 분석)
export const generatePersona = async (): Promise<PersonaGenerateResponse> => {
    const response = await api.post('/personas/generate');
    return response.data;
};

// 페르소나 수정 (선호 카테고리 저장 등)
export const updatePersona = async (data: PersonaUpdateRequest): Promise<PersonaResponse> => {
    const response = await api.patch('/personas/me', data);
    return response.data;
};
