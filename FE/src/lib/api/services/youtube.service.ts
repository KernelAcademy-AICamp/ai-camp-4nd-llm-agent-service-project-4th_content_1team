import { api } from '../client';
import type { VideoSearchRequest, VideoSearchResponse } from '../types';

// YouTube 비디오 트렌드 검색
export const searchYouTubeVideos = async (
    request: VideoSearchRequest
): Promise<VideoSearchResponse> => {
    const response = await api.post('/api/v1/youtube/search', request);
    return response.data;
};
