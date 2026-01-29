// Auth 관련 타입 정의 (추후 확장용)

export interface LoginResponse {
    tokens?: {
        accessToken: string;
        refreshToken: string;
    };
    user?: {
        id: string;
        email: string;
        name: string;
    };
}

export interface User {
    id: string;
    email: string;
    name: string;
}

export interface RefreshTokenResponse {
    accessToken: string;
    refreshToken: string;
}
