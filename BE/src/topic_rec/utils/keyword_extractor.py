"""
Keyword Extractor - TF-IDF 기반

- 글로벌 빈도(TF): 전체 트렌드에서 자주 등장하는 단어 -> 트렌드 키워드
- TF-IDF: 각 글에서 고유하게 중요한 단어 -> 개별 키워드
"""

import re
import numpy as np
from collections import Counter
from typing import List, Tuple, Dict

from sklearn.feature_extraction.text import TfidfVectorizer

from src.topic_rec.state import TrendItem

# sklearn "english" 불용어 + 플랫폼/뉴스 노이즈 + 일반 동사/형용사
EXTRA_STOPWORDS = {
    # 플랫폼 노이즈
    "hn", "askhn", "showhn", "reddit", "subreddit",
    "post", "posts", "comment", "comments", "thread",
    # 뉴스 노이즈
    "report", "reported", "according", "official", "officials",
    "says", "said", "sources", "source", "news", "article", "update",
    # URL 잔해
    "https", "http", "www", "com", "org", "html", "github", "amp",
    # 범용 테크 용어 (어디서나 등장 → 구분력 없음)
    "model", "models", "data", "code", "using", "based", "app",
    "tool", "tools", "user", "users", "work", "works", "working",
    "build", "building", "system", "systems", "project",
    # 의미 없는 일반 동사/형용사/부사
    "just", "really", "think", "want", "like", "good", "best",
    "make", "use", "new", "need", "know", "way", "thing", "things",
    "got", "getting", "going", "lot", "much", "does", "did",
    "people", "time", "year", "years", "day", "days",
    # 축약형 잔여물
    "ve", "re", "ll", "don", "doesn", "didn", "isn", "wasn", "aren",
    "couldn", "wouldn", "shouldn", "hasn", "haven", "won",
}


def _build_stop_words() -> List[str]:
    """sklearn 내장 영어 불용어 + 플랫폼 노이즈"""
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    return list(ENGLISH_STOP_WORDS | EXTRA_STOPWORDS)


def extract_keywords_tfidf(
    items: List[TrendItem], top_n: int = 5,
) -> Tuple[List[TrendItem], Dict[str, int]]:
    """
    TF-IDF + 글로벌 빈도 기반 키워드 추출.

    각 아이템의 ai_tags에 키워드를 설정하고, 전체 키워드 빈도를 반환합니다.
    ai_tags = 트렌딩 키워드(여러 문서에 등장) + TF-IDF 고유 키워드

    Args:
        items: TrendItem 리스트
        top_n: 아이템당 키워드 수

    Returns:
        (items, global_freq)
        - items: ai_tags가 채워진 TrendItem 리스트
        - global_freq: {키워드(소문자): 등장 문서 수} (스코어링 빈도 부스트용)
    """
    if not items:
        return items, {}

    texts = [f"{item.title} {item.content}" for item in items]

    # 원본 케이스 복원 매핑 (소문자 -> 원본 표기)
    case_map = _build_case_map(texts)

    vectorizer = TfidfVectorizer(
        stop_words=_build_stop_words(),
        max_features=500,
        token_pattern=r"(?u)\b\w[\w\-\.]*\w\b",  # 최소 2글자
        preprocessor=lambda text: _filter_short_tokens(text),
        min_df=1,
        max_df=1.0,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        for item in items:
            item.ai_tags = []
        return items, {}

    feature_names = np.array(vectorizer.get_feature_names_out())

    # 글로벌 문서 빈도: 각 단어가 몇 개 문서에 등장하는지
    binary_matrix = (tfidf_matrix > 0).astype(int)
    doc_freq_array = np.array(binary_matrix.sum(axis=0)).flatten()

    global_freq = {
        feature_names[j]: int(doc_freq_array[j])
        for j in range(len(feature_names))
    }

    # 아이템별 키워드 추출
    for i, item in enumerate(items):
        keywords = _extract_item_keywords(
            tfidf_matrix[i], binary_matrix[i],
            feature_names, doc_freq_array,
            case_map, top_n,
        )
        item.ai_tags = keywords

    return items, global_freq


def _filter_short_tokens(text: str) -> str:
    """소문자 변환 + 3글자 미만 영어 토큰 제거. 코딩 관련 2글자 약어는 예외."""
    KEEP_SHORT = {"ai", "go", "js", "ui", "ux", "ml", "db", "os", "ci", "cd", "qa", "ar", "vr", "3d"}
    text = text.lower()
    words = text.split()
    filtered = []
    for w in words:
        if len(w) >= 3 or w in KEEP_SHORT:
            filtered.append(w)
    return " ".join(filtered)


def _build_case_map(texts: List[str]) -> Dict[str, str]:
    """소문자 -> 가장 흔한 원본 표기 매핑. 예: 'gpt-5' -> 'GPT-5'"""
    counts: Dict[str, Counter] = {}
    for text in texts:
        words = re.findall(r"\b\w[\w\-\.]*\w\b", text)
        for word in words:
            lower = word.lower()
            if lower not in counts:
                counts[lower] = Counter()
            counts[lower][word] += 1

    return {
        lower: counter.most_common(1)[0][0]
        for lower, counter in counts.items()
    }


def _extract_item_keywords(
    tfidf_row, binary_row,
    feature_names, doc_freq_array,
    case_map, top_n,
) -> List[str]:
    """
    개별 아이템의 키워드 추출.

    1. 트렌딩 키워드: 이 문서에 있으면서, 다른 문서에서도 2번 이상 등장한 단어
    2. TF-IDF 고유 키워드: 이 문서에서만 특별히 중요한 단어
    """
    tfidf_scores = tfidf_row.toarray().flatten()
    binary_scores = binary_row.toarray().flatten()

    # TF-IDF 상위 키워드 (이 문서의 고유 키워드)
    tfidf_top = tfidf_scores.argsort()[-top_n:][::-1]
    tfidf_keywords = [
        (feature_names[j], tfidf_scores[j])
        for j in tfidf_top if tfidf_scores[j] > 0
    ]

    # 이 문서에 있는 트렌딩 키워드 (높은 문서 빈도순)
    present = np.where(binary_scores > 0)[0]
    trending_sorted = sorted(
        present, key=lambda j: doc_freq_array[j], reverse=True,
    )
    trending_keywords = [
        (feature_names[j], int(doc_freq_array[j]))
        for j in trending_sorted[:top_n]
    ]

    # 합치기: 트렌딩(2개 이상 문서에 등장) -> TF-IDF 고유
    combined = []
    seen = set()

    for kw, freq in trending_keywords:
        if kw not in seen and freq >= 2:
            combined.append(case_map.get(kw, kw))
            seen.add(kw)

    for kw, score in tfidf_keywords:
        if kw not in seen:
            combined.append(case_map.get(kw, kw))
            seen.add(kw)

    return combined[:top_n]


# === 하위 호환 ===

def extract_keywords(text: str, top_n: int = 5) -> List[str]:
    """단일 텍스트에서 키워드 추출 (하위 호환)"""
    dummy = TrendItem(
        source="", original_id="", title=text, content="",
        link="", engagement=0,
    )
    items, _ = extract_keywords_tfidf([dummy], top_n)
    return items[0].ai_tags if items[0].ai_tags else []


def enrich_with_keywords(
    items: List[TrendItem], top_n: int = 5,
) -> List[TrendItem]:
    """하위 호환 래퍼"""
    items, _ = extract_keywords_tfidf(items, top_n)
    return items
