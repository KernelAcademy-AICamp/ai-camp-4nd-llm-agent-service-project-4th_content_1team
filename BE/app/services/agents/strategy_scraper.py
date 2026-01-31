"""
StrategyScraper - 썸네일 전략 수집 서비스

웹에서 썸네일 전략 정보를 수집하여 DB에 저장합니다.
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.thumbnail_strategy import ThumbnailStrategy


logger = logging.getLogger(__name__)


class StrategyScraper:
    """
    썸네일 전략 스크래퍼
    
    웹(DuckDuckGo 등)에서 썸네일 전략 정보를 검색하고,
    LLM으로 정리하여 DB에 저장합니다.
    
    Example:
        >>> async with get_db_session() as session:
        >>>     scraper = StrategyScraper()
        >>>     await scraper.run(session)
    """
    
    def __init__(self):
        """StrategyScraper 초기화"""
        self.logger = logger
    
    async def run(
        self, 
        session: AsyncSession,
        strategies: Optional[List[Dict]] = None
    ) -> int:
        """
        전략 수집 및 DB 저장
        
        Args:
            session: 비동기 DB 세션
            strategies: 직접 제공된 전략 리스트 (없으면 웹 스크래핑)
                        [{"id": "...", "name_kr": "...", "content": "...", "source_url": "..."}]
            
        Returns:
            int: 저장된 전략 개수
            
        Example:
            >>> # 웹에서 자동 수집 (나중에 구현)
            >>> count = await scraper.run(session)
            
            >>> # 직접 제공
            >>> strategies = [{"id": "curiosity_gap", ...}]
            >>> count = await scraper.run(session, strategies=strategies)
        """
        if strategies is None:
            # TODO: 웹 스크래핑 구현 (Phase 2)
            self.logger.info("Web scraping not implemented yet")
            return 0
        
        saved_count = 0
        for strategy_data in strategies:
            try:
                await self._save_to_db(session, strategy_data)
                saved_count += 1
                self.logger.info(f"Saved strategy: {strategy_data['id']}")
            except Exception as e:
                self.logger.error(f"Failed to save strategy {strategy_data.get('id')}: {e}")
        
        await session.commit()
        return saved_count
    
    async def _save_to_db(
        self, 
        session: AsyncSession, 
        strategy_data: Dict
    ) -> ThumbnailStrategy:
        """
        전략을 DB에 저장 (Upsert)
        
        존재하면 업데이트, 없으면 생성합니다.
        
        Args:
            session: 비동기 DB 세션
            strategy_data: 전략 데이터
                {
                    "id": "curiosity_gap",
                    "name_kr": "호기심 자극형",
                    "content": "...",
                    "source_url": "https://..."
                }
            
        Returns:
            ThumbnailStrategy: 저장된 전략 객체
        """
        # 기존 전략 확인
        result = await session.execute(
            select(ThumbnailStrategy).where(
                ThumbnailStrategy.id == strategy_data["id"]
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # 업데이트
            existing.name_kr = strategy_data.get("name_kr", existing.name_kr)
            existing.content = strategy_data.get("content", existing.content)
            existing.source_url = strategy_data.get("source_url", existing.source_url)
            self.logger.info(f"Updated existing strategy: {existing.id}")
            return existing
        else:
            # 새로 생성
            new_strategy = ThumbnailStrategy(
                id=strategy_data["id"],
                name_kr=strategy_data["name_kr"],
                content=strategy_data["content"],
                source_url=strategy_data.get("source_url")
            )
            session.add(new_strategy)
            self.logger.info(f"Created new strategy: {new_strategy.id}")
            return new_strategy
    
    async def _scrape_from_web(self) -> List[Dict]:
        """
        웹에서 전략 정보 스크래핑 (TODO: Phase 2)
        
        Returns:
            List[Dict]: 전략 데이터 리스트
        """
        # TODO: DuckDuckGo 검색 구현
        # TODO: LLM으로 정리
        raise NotImplementedError("Web scraping not implemented yet")
    
    async def delete_strategy(
        self, 
        session: AsyncSession, 
        strategy_id: str
    ) -> bool:
        """
        특정 전략 삭제
        
        Args:
            session: 비동기 DB 세션
            strategy_id: 삭제할 전략 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        result = await session.execute(
            select(ThumbnailStrategy).where(
                ThumbnailStrategy.id == strategy_id
            )
        )
        strategy = result.scalar_one_or_none()
        
        if strategy:
            await session.delete(strategy)
            await session.commit()
            self.logger.info(f"Deleted strategy: {strategy_id}")
            return True
        else:
            self.logger.warning(f"Strategy not found: {strategy_id}")
            return False
