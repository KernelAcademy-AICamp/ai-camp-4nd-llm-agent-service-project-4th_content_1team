"""
ThumbnailStrategy 모델 - 썸네일 전략 관리

썸네일 생성에 사용되는 전략(Visual Strategy)을 DB에 저장하고 관리합니다.
각 전략은 고유한 ID와 한글 이름, 상세 내용을 가지며,
VisualDirector Agent가 이 전략을 기반으로 썸네일 컨셉을 결정합니다.
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship

from app.core.db import Base


class ThumbnailStrategy(Base):
    """
    썸네일 전략 테이블
    
    각 전략은 특정 심리적 트리거(호기심, 신뢰, 감정 등)를 기반으로 하며,
    비주얼 가이드라인, 색상 팔레트, 구도 등의 정보를 포함합니다.
    
    Examples:
        - curiosity_gap: 호기심 자극형
        - authority: 전문성/신뢰 구축형
        - emotional: 감정적 연결형
    """
    __tablename__ = "thumbnail_strategies"
    
    # --- 기본 정보 ---
    id = Column(String(255), primary_key=True)
    # 전략 고유 ID (예: "curiosity_gap", "authority", "emotional")
    
    name_kr = Column(String(100), nullable=False)
    # 한글 디스플레이 이름 (예: "호기심 자극형", "전문성 구축형")
    
    content = Column(Text, nullable=False)
    # 전략 상세 내용 (Markdown 형식)
    # - 핵심 컨셉
    # - 심리적 트리거
    # - 비주얼 가이드라인
    # - 색상 팔레트
    # - 구도 제안
    
    source_url = Column(String(500), nullable=True)
    # 전략 출처 URL (스크래핑 시 기록, 선택사항)
    
    # --- 메타데이터 ---
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # --- Relationships ---
    # ThumbnailGeneration에서 전략 ID를 JSON으로 저장하므로 relationship 불필요
    
    def __repr__(self):
        return f"<ThumbnailStrategy(id={self.id}, name={self.name_kr})>"
