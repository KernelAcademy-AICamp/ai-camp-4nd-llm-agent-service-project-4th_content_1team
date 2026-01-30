"""
Visual Director Agent 테스트
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.visual_director import VisualDirectorAgent


@pytest.fixture
def visual_director():
    """VisualDirectorAgent 인스턴스"""
    return VisualDirectorAgent()


@pytest.fixture
def sample_headline():
    """샘플 제목"""
    return {
        "main_title": "AI 칩 전쟁",
        "sub_title": "삼성이 반격한다",
        "style_type": "secret",
        "keywords_used": ["AI 반도체", "삼성전자"]
    }


@pytest.fixture
def sample_keywords():
    """샘플 키워드"""
    return ["AI 반도체", "엔비디아", "삼성전자"]


@pytest.fixture
def sample_summary():
    """샘플 요약"""
    return "AI 반도체 시장이 급성장하고 있으며, 엔비디아가 GPU 시장을 독점하고 있습니다. 삼성전자는 HBM 메모리 개발로 반격을 준비중입니다."


@pytest.fixture
def sample_image_refs():
    """샘플 이미지 레퍼런스"""
    return {
        "ref_layout": "layout_001.jpg",
        "ref_person": "person_001.jpg",
        "ref_asset": "asset_001.png",
        "ref_style": "style_001.jpg"
    }


@pytest.fixture
def sample_visual_strategy():
    """샘플 Visual Strategy"""
    return {
        "purpose": "AI 반도체 시장의 치열한 경쟁을 시각화",
        "main_subject": {
            "description": "다크 수트를 입은 아시아 남성 CEO",
            "position": "center",
            "size": "large"
        },
        "background": {
            "type": "gradient",
            "description": "다크 블루에서 네이비로 이어지는 그라데이션",
            "effects": ["vignette", "glow"]
        },
        "elements": [
            {
                "type": "text",
                "content": "AI 칩 전쟁",
                "position": "top-center",
                "style": "bold sans-serif, white"
            }
        ],
        "camera": {
            "angle": "eye-level",
            "shot_type": "medium-shot",
            "lighting": "dramatic",
            "depth_of_field": "shallow"
        },
        "style": "photorealistic",
        "mood": "intense, competitive",
        "color_palette": {
            "primary": ["#0A1929", "#1A2332"],
            "accent": ["#FF0000"],
            "text": "#FFFFFF"
        },
        "avoid": "cartoonish, bright colors"
    }


@pytest.mark.asyncio
async def test_create_visual_strategy(
    visual_director,
    sample_headline,
    sample_keywords,
    sample_summary,
    sample_image_refs,
    sample_visual_strategy
):
    """Visual Strategy 생성 테스트"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=f"```json\n{json.dumps(sample_visual_strategy, ensure_ascii=False)}\n```"
            )
        )
    ]
    
    with patch.object(
        visual_director.client.chat.completions,
        'create',
        new_callable=AsyncMock,
        return_value=mock_response
    ):
        result = await visual_director.create_visual_strategy(
            headline=sample_headline,
            keywords=sample_keywords,
            script_summary=sample_summary,
            image_refs=sample_image_refs
        )
        
        # 검증
        assert result is not None
        assert "purpose" in result
        assert "main_subject" in result
        assert "background" in result
        assert "elements" in result
        assert "camera" in result
        assert "style" in result
        assert "mood" in result
        assert "color_palette" in result
        assert "avoid" in result
        assert "image_refs" in result
        assert result["image_refs"] == sample_image_refs


@pytest.mark.asyncio
async def test_create_visual_strategy_no_image_refs(
    visual_director,
    sample_headline,
    sample_keywords,
    sample_summary,
    sample_visual_strategy
):
    """이미지 레퍼런스 없이 Visual Strategy 생성 테스트"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=f"```json\n{json.dumps(sample_visual_strategy, ensure_ascii=False)}\n```"
            )
        )
    ]
    
    with patch.object(
        visual_director.client.chat.completions,
        'create',
        new_callable=AsyncMock,
        return_value=mock_response
    ):
        result = await visual_director.create_visual_strategy(
            headline=sample_headline,
            keywords=sample_keywords,
            script_summary=sample_summary
        )
        
        # 검증
        assert result is not None
        assert "image_refs" not in result


@pytest.mark.asyncio
async def test_create_visual_strategy_empty_headline(
    visual_director,
    sample_keywords,
    sample_summary
):
    """빈 제목 에러 테스트"""
    with pytest.raises(ValueError, match="제목 정보가 없습니다"):
        await visual_director.create_visual_strategy(
            headline=None,
            keywords=sample_keywords,
            script_summary=sample_summary
        )


@pytest.mark.asyncio
async def test_create_visual_strategy_no_main_title(
    visual_director,
    sample_keywords,
    sample_summary
):
    """메인 제목 없음 에러 테스트"""
    with pytest.raises(ValueError, match="메인 제목이 없습니다"):
        await visual_director.create_visual_strategy(
            headline={"sub_title": "서브 제목"},
            keywords=sample_keywords,
            script_summary=sample_summary
        )


def test_create_user_prompt(
    visual_director,
    sample_headline,
    sample_keywords,
    sample_summary,
    sample_image_refs
):
    """사용자 프롬프트 생성 테스트"""
    prompt = visual_director._create_user_prompt(
        headline=sample_headline,
        keywords=sample_keywords,
        script_summary=sample_summary,
        image_refs=sample_image_refs
    )
    
    # 검증
    assert "AI 칩 전쟁" in prompt
    assert "삼성이 반격한다" in prompt
    assert "secret" in prompt
    assert "AI 반도체" in prompt
    assert "엔비디아" in prompt
    assert sample_summary in prompt
    assert "layout_001.jpg" in prompt
    assert "person_001.jpg" in prompt


def test_parse_response(visual_director, sample_visual_strategy):
    """응답 파싱 테스트"""
    # JSON 코드 블록 포함
    content = f"```json\n{json.dumps(sample_visual_strategy, ensure_ascii=False)}\n```"
    
    result = visual_director._parse_response(content)
    
    # 검증
    assert result == sample_visual_strategy


def test_parse_response_no_code_block(visual_director, sample_visual_strategy):
    """코드 블록 없는 응답 파싱 테스트"""
    content = json.dumps(sample_visual_strategy, ensure_ascii=False)
    
    result = visual_director._parse_response(content)
    
    # 검증
    assert result == sample_visual_strategy


def test_parse_response_invalid_json(visual_director):
    """잘못된 JSON 파싱 에러 테스트"""
    content = "{ invalid json }"
    
    with pytest.raises(ValueError, match="JSON 파싱 실패"):
        visual_director._parse_response(content)


def test_parse_response_missing_field(visual_director):
    """필수 필드 누락 에러 테스트"""
    incomplete_strategy = {
        "purpose": "test",
        "main_subject": {}
        # 나머지 필드 누락
    }
    
    content = json.dumps(incomplete_strategy)
    
    with pytest.raises(ValueError, match="필수 필드 누락"):
        visual_director._parse_response(content)


def test_get_model_info(visual_director):
    """모델 정보 반환 테스트"""
    info = visual_director.get_model_info()
    
    assert info["model"] == "gpt-4o"
    assert info["temperature"] == 0.7
    assert info["max_tokens"] == 1500
