export interface SubtitleFetchRequest {
    video_ids: string[];
    languages?: string[];
}

export interface SubtitleCue {
    start: number;
    end: number;
    text: string;
}

export interface SubtitleTrack {
    language_code: string;
    language_name: string;
    is_auto_generated: boolean;
    cues: SubtitleCue[];
}

export interface SubtitleResult {
    video_id: string;
    status: "success" | "no_subtitle" | "failed";
    source?: string | null;
    tracks: SubtitleTrack[];
    no_captions: boolean;
    error?: string | null;
}

export interface SubtitleFetchResponse {
    results: SubtitleResult[];
}
