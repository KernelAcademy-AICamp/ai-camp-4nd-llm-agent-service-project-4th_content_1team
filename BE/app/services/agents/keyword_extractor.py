"""
KeywordExtractorAgent - 키워드 추출 에이전트

TF-IDF 알고리즘을 사용하여 스크립트에서 핵심 키워드 10-15개를 추출합니다.
"""
import logging
import re
from typing import List, Set
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


logger = logging.getLogger(__name__)


# 한글 불용어 리스트
KOREAN_STOPWORDS = {
    # 조사
    "이", "가", "을", "를", "에", "에서", "으로", "로", "와", "과", "의", "도", "은", "는",
    "만", "부터", "까지", "께서", "에게", "한테", "보다", "처럼", "같이",
    
    # 접속사
    "그리고", "하지만", "그러나", "그런데", "또한", "또", "및", "혹은", "즉",
    
    # 대명사
    "이것", "그것", "저것", "여기", "거기", "저기", "이곳", "그곳", "저곳",
    "나", "너", "우리", "저희", "당신", "그", "그녀", "그들",
    
    # 수식어
    "이런", "그런", "저런", "어떤", "모든", "각", "매", "아무",
    
    # 동사/형용사 어미
    "다", "입니다", "습니다", "ㅂ니다", "니다", "있다", "없다", "하다",
    
    # 기타
    "등", "및", "좀", "더", "덜", "아주", "매우", "정말", "참", "과연",
    "것", "수", "때", "곳", "점", "바"
}


class KeywordExtractorAgent:
    """
    키워드 추출 에이전트
    
    TF-IDF 알고리즘을 사용하여 스크립트에서 핵심 키워드를 추출합니다.
    
    Example:
        >>> extractor = KeywordExtractorAgent()
        >>> keywords = await extractor.extract(
        ...     script_full="AI 반도체 시장이 급성장하고 있습니다...",
        ...     script_summary="AI 반도체 시장 분석"
        ... )
        >>> print(keywords)
        ['AI', '반도체', '시장', '급성장', ...]
    """
    
    def __init__(self, min_keywords: int = 10, max_keywords: int = 15):
        """
        KeywordExtractorAgent 초기화
        
        Args:
            min_keywords: 최소 키워드 개수 (기본값: 10)
            max_keywords: 최대 키워드 개수 (기본값: 15)
        """
        self.min_keywords = min_keywords
        self.max_keywords = max_keywords
        self.logger = logger
    
    async def extract(
        self, 
        script_full: str, 
        script_summary: str = ""
    ) -> List[str]:
        """
        스크립트에서 핵심 키워드 추출
        
        Args:
            script_full: 전체 스크립트 텍스트
            script_summary: 스크립트 요약 (선택사항)
            
        Returns:
            List[str]: 추출된 키워드 리스트 (10-15개)
            
        Raises:
            ValueError: 스크립트가 비어있거나 너무 짧은 경우
            
        Example:
            >>> keywords = await extractor.extract(
            ...     script_full="AI 반도체 시장이 급성장...",
            ...     script_summary="AI 반도체 분석"
            ... )
        """
        # 입력 검증
        if not script_full or len(script_full.strip()) < 50:
            raise ValueError("스크립트가 너무 짧습니다 (최소 50자 필요)")
        
        self.logger.info(f"키워드 추출 시작 (스크립트 길이: {len(script_full)}자)")
        
        try:
            # 1. 텍스트 전처리
            processed_text = self._preprocess_text(script_full)
            if script_summary:
                processed_summary = self._preprocess_text(script_summary)
                # 요약을 2배 가중치로 추가
                processed_text = f"{processed_summary} {processed_summary} {processed_text}"
            
            # 2. TF-IDF로 키워드 추출
            keywords = self._extract_with_tfidf(processed_text)
            
            # 3. 불용어 제거
            keywords = self._remove_stopwords(keywords)
            
            # 4. 개수 조정
            if len(keywords) < self.min_keywords:
                self.logger.warning(
                    f"추출된 키워드가 {len(keywords)}개로 최소 개수({self.min_keywords})보다 적습니다"
                )
            keywords = keywords[:self.max_keywords]
            
            self.logger.info(f"키워드 추출 완료: {len(keywords)}개")
            return keywords
        
        except Exception as e:
            self.logger.error(f"키워드 추출 실패: {e}")
            raise
    
    def _preprocess_text(self, text: str) -> str:
        """
        텍스트 전처리
        
        Args:
            text: 원본 텍스트
            
        Returns:
            str: 전처리된 텍스트
        """
        # 소문자 변환
        text = text.lower()
        
        # 특수문자 제거 (한글, 영문, 숫자, 공백만 남김)
        text = re.sub(r'[^가-힣a-z0-9\s]', ' ', text)
        
        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _extract_with_tfidf(self, text: str) -> List[str]:
        """
        TF-IDF로 키워드 추출
        
        Args:
            text: 전처리된 텍스트
            
        Returns:
            List[str]: TF-IDF 점수가 높은 키워드 리스트
        """
        # TfidfVectorizer 초기화
        vectorizer = TfidfVectorizer(
            max_features=50,  # 상위 50개 후보
            ngram_range=(1, 2),  # 1-gram, 2-gram
            min_df=1,
            token_pattern=r'(?u)\b\w+\b'
        )
        
        try:
            # TF-IDF 행렬 생성
            tfidf_matrix = vectorizer.fit_transform([text])
            
            # 특성 이름 (단어들)
            feature_names = vectorizer.get_feature_names_out()
            
            # TF-IDF 점수
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # 점수가 높은 순으로 정렬
            sorted_indices = np.argsort(tfidf_scores)[::-1]
            
            # 키워드 추출
            keywords = [
                feature_names[idx] 
                for idx in sorted_indices 
                if tfidf_scores[idx] > 0
            ]
            
            return keywords
        
        except Exception as e:
            self.logger.error(f"TF-IDF 추출 실패: {e}")
            # Fallback: 단순 빈도 기반
            return self._extract_by_frequency(text)
    
    def _extract_by_frequency(self, text: str) -> List[str]:
        """
        빈도 기반 키워드 추출 (Fallback)
        
        Args:
            text: 전처리된 텍스트
            
        Returns:
            List[str]: 빈도가 높은 키워드 리스트
        """
        # 단어 분리
        words = text.split()
        
        # 빈도 계산
        word_freq = {}
        for word in words:
            if len(word) > 1:  # 1글자 제외
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 빈도순 정렬
        sorted_words = sorted(
            word_freq.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return [word for word, freq in sorted_words[:50]]
    
    def _remove_stopwords(self, keywords: List[str]) -> List[str]:
        """
        불용어 제거
        
        Args:
            keywords: 키워드 리스트
            
        Returns:
            List[str]: 불용어가 제거된 키워드 리스트
        """
        filtered = []
        seen: Set[str] = set()
        
        for keyword in keywords:
            # 소문자 변환
            keyword_lower = keyword.lower()
            
            # 불용어 체크
            if keyword_lower in KOREAN_STOPWORDS:
                continue
            
            # 1글자 단어 제외
            if len(keyword) < 2:
                continue
            
            # 중복 제거
            if keyword_lower in seen:
                continue
            
            # 숫자만 있는 경우 제외
            if keyword.isdigit():
                continue
            
            filtered.append(keyword)
            seen.add(keyword_lower)
        
        return filtered
    
    def get_keyword_count(self) -> tuple[int, int]:
        """
        설정된 키워드 개수 범위 반환
        
        Returns:
            tuple[int, int]: (최소 개수, 최대 개수)
        """
        return (self.min_keywords, self.max_keywords)
