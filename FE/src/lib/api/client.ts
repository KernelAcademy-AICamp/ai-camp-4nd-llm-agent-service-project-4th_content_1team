import axios from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
})

// 로그인 후 API 호출 시 localStorage의 accessToken을 Bearer로 첨부 (계정 분기 등 인증 필요)
api.interceptors.request.use((config) => {
  if (typeof window === "undefined") return config
  const token = localStorage.getItem("accessToken")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
