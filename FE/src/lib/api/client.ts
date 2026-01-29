import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
    baseURL: API_URL,
    withCredentials: true, // 쿠키 전송을 위해 필요
    headers: {
        'Content-Type': 'application/json',
    },
});
