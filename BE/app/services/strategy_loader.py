"""
StrategyLoader - 썸네일 전략 로딩 서비스

DB에서 ThumbnailStrategy를 조회하여 에이전트에 제공합니다.
"""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.thumbnail_strategy import ThumbnailStrategy


class StrategyLoader:
    """
    썸네일 전략 로딩 서비스
    
    DB에서 저장된 썸네일 전략(ThumbnailStrategy)을 조회하여
    VisualDirector Agent 등에서 사용할 수 있도록 제공합니다.
    
    Example:
        >>> async with get_db_session() as session:
        >>>     loader = StrategyLoader()
        >>>     strategies = await loader.get_all_strategies(session)
        >>>     print(f"Loaded {len(strategies)} strategies")
    """
    
    async def get_all_strategies(self, session: AsyncSession) -> List[ThumbnailStrategy]:
        """
        모든 썸네일 전략 조회
        
        Args:
            session: 비동기 DB 세션
            
        Returns:
            List[ThumbnailStrategy]: 전략 리스트 (created_at 오름차순)
            
        Example:
            >>> strategies = await loader.get_all_strategies(session)
            >>> for strategy in strategies:
            >>>     print(f"{strategy.id}: {strategy.name_kr}")
        """
        result = await session.execute(
            select(ThumbnailStrategy).order_by(ThumbnailStrategy.created_at)
        )
        return result.scalars().all()
    
    async def get_strategy_by_id(
        self, 
        session: AsyncSession, 
        strategy_id: str
    ) -> Optional[ThumbnailStrategy]:
        """
        특정 ID의 전략 조회
        
        Args:
            session: 비동기 DB 세션
            strategy_id: 전략 ID (예: "curiosity_gap")
            
        Returns:
            Optional[ThumbnailStrategy]: 전략 객체 (없으면 None)
            
        Example:
            >>> strategy = await loader.get_strategy_by_id(session, "curiosity_gap")
            >>> if strategy:
            >>>     print(strategy.content)
        """
        result = await session.execute(
            select(ThumbnailStrategy).where(ThumbnailStrategy.id == strategy_id)
        )
        return result.scalar_one_or_none()
    
    async def get_strategies_by_ids(
        self, 
        session: AsyncSession, 
        strategy_ids: List[str]
    ) -> List[ThumbnailStrategy]:
        """
        여러 ID의 전략 조회
        
        Args:
            session: 비동기 DB 세션
            strategy_ids: 전략 ID 리스트 (예: ["curiosity_gap", "loss_aversion"])
            
        Returns:
            List[ThumbnailStrategy]: 전략 리스트
            
        Example:
            >>> ids = ["curiosity_gap", "loss_aversion"]
            >>> strategies = await loader.get_strategies_by_ids(session, ids)
        """
        result = await session.execute(
            select(ThumbnailStrategy).where(ThumbnailStrategy.id.in_(strategy_ids))
        )
        return result.scalars().all()
    
    async def get_strategy_count(self, session: AsyncSession) -> int:
        """
        저장된 전략 개수 확인
        
        Args:
            session: 비동기 DB 세션
            
        Returns:
            int: 전략 개수
            
        Example:
            >>> count = await loader.get_strategy_count(session)
            >>> print(f"Total strategies: {count}")
        """
        result = await session.execute(select(ThumbnailStrategy))
        strategies = result.scalars().all()
        return len(strategies)
    
    def format_strategy_for_llm(self, strategy: ThumbnailStrategy) -> str:
        """
        전략을 LLM 프롬프트용 텍스트로 변환
        
        VisualDirector Agent에서 전략을 선택할 때 사용합니다.
        
        Args:
            strategy: 전략 객체
            
        Returns:
            str: 프롬프트용 포맷팅된 텍스트
            
        Example:
            >>> strategy = await loader.get_strategy_by_id(session, "curiosity_gap")
            >>> formatted = loader.format_strategy_for_llm(strategy)
            >>> # "ID: curiosity_gap\n이름: 호기심 자극형\n설명: ..."
        """
        return f"""ID: {strategy.id}
이름: {strategy.name_kr}
설명: {strategy.content}
출처: {strategy.source_url or 'N/A'}
"""
    
    def format_all_strategies_for_llm(
        self, 
        strategies: List[ThumbnailStrategy]
    ) -> str:
        """
        모든 전략을 LLM 프롬프트용 텍스트로 변환
        
        Args:
            strategies: 전략 리스트
            
        Returns:
            str: 프롬프트용 포맷팅된 전체 텍스트
            
        Example:
            >>> strategies = await loader.get_all_strategies(session)
            >>> prompt_text = loader.format_all_strategies_for_llm(strategies)
        """
        formatted_list = [
            self.format_strategy_for_llm(strategy) 
            for strategy in strategies
        ]
        return "\n\n---\n\n".join(formatted_list)
