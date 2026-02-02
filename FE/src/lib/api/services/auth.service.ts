import { api } from '../client';
import type { LoginResponse, User, RefreshTokenResponse } from '../types';

// Google OAuth 로그인
export const googleLogin = async (code: string, redirectUri: string): Promise<LoginResponse> => {
    const response = await api.post('/auth/google/callback', {
        code,
        redirectUri,
    });
    return response.data;
};

// 현재 사용자 조회
export const getCurrentUser = async (): Promise<User> => {
    const response = await api.get('/auth/me');
    return response.data;
};

// 로그아웃
export const logout = async (): Promise<void> => {
    const response = await api.post('/auth/logout');
    return response.data;
};

// 토큰 갱신
export const refreshToken = async (refreshTokenValue: string): Promise<RefreshTokenResponse> => {
    const response = await api.post('/auth/refresh', {
        refreshToken: refreshTokenValue,
    });
    return response.data;
};
