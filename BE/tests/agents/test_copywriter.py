"""
CopywriterAgent 테스트
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.agents.copywriter import CopywriterAgent


@pytest.fixture
def copywriter():
    """CopywriterAgent 인스턴스"""
    return CopywriterAgent()


@pytest.fixture
def sample_keywords():
    """샘플 키워드"""
    return ["AI 반도체", "엔비디아", "삼성전자"]


@pytest.fixture
def sample_summary():
    """샘플 요약"""
    return "AI 반도체 시장 분석 및 주요 기업 동향"


@pytest.fixture
def sample_llm_response():
    """샘플 LLM 응답"""
    return json.dumps({
        "title_sets": [
            {
                "id": 1,
                "main_title": "AI 칩 전쟁",
                "sub_title": "삼성이 반격한다",
                "style_type": "secret",
                "keywords_used": ["AI 반도체", "삼성전자"],
                "rationale": "비밀형 스타일로 전쟁과 반격 구조 사용"
            },
            {
                "id": 2,
                "main_title": "모르면 손해",
                "sub_title": "엔비디아 독점의 진실",
                "style_type": "avoidance",
                "keywords_used": ["엔비디아"],
                "rationale": "회피형 스타일로 손실 회피 심리 자극"
            },
            {
                "id": 3,
                "main_title": "TOP 3 기업",
                "sub_title": "2026 AI 반도체 판도",
                "style_type": "number",
                "keywords_used": ["AI 반도체"],
                "rationale": "숫자형 스타일로 명확한 구조 제시"
            }
        ]
    })


@pytest.mark.asyncio
@patch('app.services.agents.copywriter.AsyncOpenAI')
async def test_generate_headlines(
    mock_openai,
    copywriter,
    sample_keywords,
    sample_summary,
    sample_llm_response
):
    """제목 생성 테스트"""
    # Mock LLM 응답
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = sample_llm_response
    
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response
    copywriter.client = mock_client
    
    # 실행
    title_sets = await copywriter.generate_headlines(
        keywords=sample_keywords,
        script_summary=sample_summary
    )
    
    # 검증
    assert len(title_sets) == 3
    assert all(isinstance(ts, dict) for ts in title_sets)
    
    # 첫 번째 제목 세트 검증
    first_set = title_sets[0]
    assert first_set["main_title"] == "AI 칩 전쟁"
    assert first_set["sub_title"] == "삼성이 반격한다"
    assert first_set["style_type"] == "secret"
    assert "keywords_used" in first_set
    assert "rationale" in first_set


@pytest.mark.asyncio
async def test_generate_headlines_empty_keywords(copywriter, sample_summary):
    """빈 키워드 에러 테스트"""
    with pytest.raises(ValueError, match="키워드가 비어있습니다"):
        await copywriter.generate_headlines(
            keywords=[],
            script_summary=sample_summary
        )


@pytest.mark.asyncio
async def test_generate_headlines_empty_summary(copywriter, sample_keywords):
    """빈 요약 에러 테스트"""
    with pytest.raises(ValueError, match="스크립트 요약이 비어있습니다"):
        await copywriter.generate_headlines(
            keywords=sample_keywords,
            script_summary=""
        )


def test_create_user_prompt(copywriter, sample_keywords, sample_summary):
    """사용자 프롬프트 생성 테스트"""
    prompt = copywriter._create_user_prompt(
        keywords=sample_keywords,
        script_summary=sample_summary
    )
    
    # 검증
    assert "맥락" in prompt
    assert "선택된 키워드" in prompt
    assert sample_summary in prompt
    for keyword in sample_keywords:
        assert keyword in prompt


def test_parse_response(copywriter, sample_llm_response):
    """LLM 응답 파싱 테스트"""
    title_sets = copywriter._parse_response(sample_llm_response)
    
    # 검증
    assert len(title_sets) == 3
    assert all("id" in ts for ts in title_sets)
    assert all("main_title" in ts for ts in title_sets)
    assert all("sub_title" in ts for ts in title_sets)
    assert all("style_type" in ts for ts in title_sets)
    assert all("keywords_used" in ts for ts in title_sets)
    assert all("rationale" in ts for ts in title_sets)


def test_parse_response_invalid_json(copywriter):
    """잘못된 JSON 파싱 테스트"""
    with pytest.raises(ValueError, match="JSON으로 파싱할 수 없습니다"):
        copywriter._parse_response("invalid json")


def test_parse_response_missing_field(copywriter):
    """필수 필드 누락 테스트"""
    invalid_response = json.dumps({
        "title_sets": [
            {
                "id": 1,
                "main_title": "제목",
                # sub_title 누락
            }
        ]
    })
    
    with pytest.raises(ValueError, match="필수 필드 누락"):
        copywriter._parse_response(invalid_response)


def test_get_model_info(copywriter):
    """모델 정보 테스트"""
    info = copywriter.get_model_info()
    
    assert "model" in info
    assert "temperature" in info
    assert "max_tokens" in info
    assert info["model"] == "gpt-4o-mini"
    assert info["temperature"] == 0.8
    assert info["max_tokens"] == 500
