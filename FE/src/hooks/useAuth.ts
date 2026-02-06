import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api/client';

interface User {
    id: string;
    email: string;
    name: string;
    avatar_url?: string;
}

export const useAuth = () => {
    const { data: user, isLoading, error, refetch } = useQuery<User | null>({
        queryKey: ['current-user'],
        queryFn: async () => {
            try {
                const response = await api.get('/auth/me');
                return response.data;
            } catch (err) {
                // 인증 실패 시 null 반환
                return null;
            }
        },
        staleTime: 1000 * 60 * 5, // 5분간 캐시
        retry: false,
    });

    return {
        user,
        isLoading,
        isAuthenticated: !!user && !error,
        refetch,
    };
};
