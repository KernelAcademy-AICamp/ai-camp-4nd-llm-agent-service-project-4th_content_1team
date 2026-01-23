import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
    baseURL: API_URL,
    withCredentials: true, // 쿠키 전송을 위해 필요
    headers: {
        'Content-Type': 'application/json',
    },
});

// Google OAuth 로그인
export const googleLogin = async (code: string, redirectUri: string) => {
    const response = await api.post('/auth/google/callback', {
        code,
        redirectUri,
    });
    return response.data;
};

// 현재 사용자 조회
export const getCurrentUser = async () => {
    const response = await api.get('/auth/me');
    return response.data;
};

// 로그아웃
export const logout = async () => {
    const response = await api.post('/auth/logout');
    return response.data;
};

// 토큰 갱신
export const refreshToken = async (refreshToken: string) => {
    const response = await api.post('/auth/refresh', {
        refreshToken,
    });
    return response.data;
};
