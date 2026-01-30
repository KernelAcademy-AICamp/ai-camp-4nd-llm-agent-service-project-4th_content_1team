"""
KeywordExtractorAgent 테스트
"""
import pytest
from app.services.agents.keyword_extractor import KeywordExtractorAgent


@pytest.fixture
def extractor():
    """KeywordExtractorAgent 인스턴스"""
    return KeywordExtractorAgent(min_keywords=10, max_keywords=15)


@pytest.fixture
def sample_script():
    """샘플 스크립트"""
    return """
    2026년 AI 반도체 시장이 급성장하고 있습니다. 
    삼성전자와 SK하이닉스가 HBM 메모리 시장에서 경쟁하고 있으며,
    엔비디아의 GPU 독점이 계속되고 있습니다.
    AI 칩 전쟁이 본격화되면서 한국 기업들의 역할이 중요해지고 있습니다.
    특히 HBM3 메모리 기술이 핵심이며, 삼성전자가 선두를 달리고 있습니다.
    AI 반도체 시장은 2030년까지 연평균 25% 성장할 것으로 예상됩니다.
    """


@pytest.fixture
def sample_summary():
    """샘플 요약"""
    return "AI 반도체 시장 분석 및 한국 기업의 경쟁력"


@pytest.mark.asyncio
async def test_extract_keywords(extractor, sample_script, sample_summary):
    """키워드 추출 테스트"""
    keywords = await extractor.extract(sample_script, sample_summary)
    
    # 검증
    assert len(keywords) >= 10
    assert len(keywords) <= 15
    assert isinstance(keywords, list)
    assert all(isinstance(kw, str) for kw in keywords)
    
    # 주요 키워드 포함 확인
    keywords_lower = [kw.lower() for kw in keywords]
    assert any('ai' in kw or '반도체' in kw for kw in keywords_lower)


@pytest.mark.asyncio
async def test_extract_without_summary(extractor, sample_script):
    """요약 없이 키워드 추출 테스트"""
    keywords = await extractor.extract(sample_script)
    
    # 검증
    assert len(keywords) >= 10
    assert len(keywords) <= 15


@pytest.mark.asyncio
async def test_empty_script(extractor):
    """빈 스크립트 에러 테스트"""
    with pytest.raises(ValueError, match="스크립트가 너무 짧습니다"):
        await extractor.extract("")


@pytest.mark.asyncio
async def test_too_short_script(extractor):
    """너무 짧은 스크립트 에러 테스트"""
    with pytest.raises(ValueError, match="스크립트가 너무 짧습니다"):
        await extractor.extract("AI 반도체")


def test_preprocess_text(extractor):
    """텍스트 전처리 테스트"""
    text = "AI 반도체!!! 시장@@@ 분석..."
    processed = extractor._preprocess_text(text)
    
    # 특수문자 제거 확인
    assert "!" not in processed
    assert "@" not in processed
    assert "." not in processed
    
    # 소문자 변환 확인
    assert processed == processed.lower()


def test_remove_stopwords(extractor):
    """불용어 제거 테스트"""
    keywords = ["AI", "반도체", "이", "가", "를", "시장", "그리고", "있다"]
    filtered = extractor._remove_stopwords(keywords)
    
    # 불용어가 제거되었는지 확인
    assert "이" not in filtered
    assert "가" not in filtered
    assert "를" not in filtered
    assert "그리고" not in filtered
    assert "있다" not in filtered
    
    # 실제 키워드는 남아있는지 확인
    assert "AI" in filtered or "ai" in filtered
    assert "반도체" in filtered
    assert "시장" in filtered


def test_remove_stopwords_duplicates(extractor):
    """중복 제거 테스트"""
    keywords = ["AI", "ai", "반도체", "반도체", "시장"]
    filtered = extractor._remove_stopwords(keywords)
    
    # 중복이 제거되었는지 확인
    assert filtered.count("AI") + filtered.count("ai") == 1
    assert filtered.count("반도체") == 1


def test_get_keyword_count(extractor):
    """키워드 개수 범위 테스트"""
    min_kw, max_kw = extractor.get_keyword_count()
    
    assert min_kw == 10
    assert max_kw == 15


@pytest.mark.asyncio
async def test_extract_with_long_script(extractor):
    """긴 스크립트 테스트"""
    long_script = """
    AI 반도체 산업이 전 세계적으로 급성장하고 있습니다.
    특히 한국의 삼성전자와 SK하이닉스는 HBM(High Bandwidth Memory) 메모리 분야에서
    세계 시장을 선도하고 있습니다. HBM3 기술은 AI 학습과 추론에 필수적이며,
    엔비디아의 GPU와 결합되어 사용됩니다.
    
    삼성전자는 최근 HBM3E 양산을 시작했으며, SK하이닉스도 HBM3 12단 제품을
    출시했습니다. 두 회사 모두 2026년까지 HBM 생산능력을 2배 이상 확대할 계획입니다.
    
    AI 칩 전쟁은 단순히 반도체 기업들만의 경쟁이 아닙니다.
    클라우드 서비스 기업들도 자체 AI 칩을 개발하고 있으며,
    구글의 TPU, 아마존의 Trainium 등이 대표적입니다.
    
    향후 AI 반도체 시장은 2030년까지 연평균 25% 이상 성장하여
    5000억 달러 규모에 달할 것으로 전망됩니다.
    """ * 2  # 더 길게
    
    keywords = await extractor.extract(long_script)
    
    # 검증
    assert len(keywords) >= 10
    assert len(keywords) <= 15
    
    # 주요 키워드 확인
    keywords_str = " ".join(keywords).lower()
    assert "ai" in keywords_str or "반도체" in keywords_str
