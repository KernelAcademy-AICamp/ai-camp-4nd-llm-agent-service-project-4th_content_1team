export interface NewsSearchRequest {
    keywords: string[];
    max_results_per_keyword?: number;
}

export interface NewsArticle {
    title: string;
    url: string;
    content?: string;
    published_date?: string;
    source?: string;
    keyword: string;
}

export interface NewsSearchResponse {
    total_results: number;
    articles: NewsArticle[];
}
