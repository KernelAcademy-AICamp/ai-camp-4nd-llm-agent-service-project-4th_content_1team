"""
StrategyLoader 테스트
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.strategy_loader import StrategyLoader
from app.models.thumbnail_strategy import ThumbnailStrategy


@pytest.fixture
def strategy_loader():
    """StrategyLoader 인스턴스"""
    return StrategyLoader()


@pytest.fixture
def mock_session():
    """Mock AsyncSession"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_strategies():
    """샘플 전략 데이터"""
    return [
        ThumbnailStrategy(
            id="curiosity_gap",
            name_kr="호기심 자극형",
            content="호기심을 자극하는 전략",
            source_url="https://example.com"
        ),
        ThumbnailStrategy(
            id="loss_aversion",
            name_kr="손실 회피형",
            content="손실을 회피하는 전략",
            source_url="https://example.com"
        ),
    ]


@pytest.mark.asyncio
async def test_get_all_strategies(strategy_loader, mock_session, sample_strategies):
    """모든 전략 조회 테스트"""
    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = sample_strategies
    mock_session.execute.return_value = mock_result
    
    # 실행
    strategies = await strategy_loader.get_all_strategies(mock_session)
    
    # 검증
    assert len(strategies) == 2
    assert strategies[0].id == "curiosity_gap"
    assert strategies[1].id == "loss_aversion"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_strategy_by_id(strategy_loader, mock_session, sample_strategies):
    """특정 ID 전략 조회 테스트"""
    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_strategies[0]
    mock_session.execute.return_value = mock_result
    
    # 실행
    strategy = await strategy_loader.get_strategy_by_id(mock_session, "curiosity_gap")
    
    # 검증
    assert strategy is not None
    assert strategy.id == "curiosity_gap"
    assert strategy.name_kr == "호기심 자극형"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_strategy_by_id_not_found(strategy_loader, mock_session):
    """존재하지 않는 ID 조회 테스트"""
    # Mock execute result (None 반환)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # 실행
    strategy = await strategy_loader.get_strategy_by_id(mock_session, "nonexistent")
    
    # 검증
    assert strategy is None
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_strategies_by_ids(strategy_loader, mock_session, sample_strategies):
    """여러 ID 전략 조회 테스트"""
    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = sample_strategies
    mock_session.execute.return_value = mock_result
    
    # 실행
    strategies = await strategy_loader.get_strategies_by_ids(
        mock_session, 
        ["curiosity_gap", "loss_aversion"]
    )
    
    # 검증
    assert len(strategies) == 2
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_strategy_count(strategy_loader, mock_session, sample_strategies):
    """전략 개수 확인 테스트"""
    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = sample_strategies
    mock_session.execute.return_value = mock_result
    
    # 실행
    count = await strategy_loader.get_strategy_count(mock_session)
    
    # 검증
    assert count == 2
    mock_session.execute.assert_called_once()


def test_format_strategy_for_llm(strategy_loader, sample_strategies):
    """전략 LLM 포맷 변환 테스트"""
    strategy = sample_strategies[0]
    
    # 실행
    formatted = strategy_loader.format_strategy_for_llm(strategy)
    
    # 검증
    assert "ID: curiosity_gap" in formatted
    assert "이름: 호기심 자극형" in formatted
    assert "설명: 호기심을 자극하는 전략" in formatted
    assert "출처: https://example.com" in formatted


def test_format_all_strategies_for_llm(strategy_loader, sample_strategies):
    """모든 전략 LLM 포맷 변환 테스트"""
    # 실행
    formatted = strategy_loader.format_all_strategies_for_llm(sample_strategies)
    
    # 검증
    assert "curiosity_gap" in formatted
    assert "loss_aversion" in formatted
    assert "---" in formatted  # 구분자 확인
