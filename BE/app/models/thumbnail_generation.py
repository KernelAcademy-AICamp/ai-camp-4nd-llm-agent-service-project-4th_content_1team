"""
ThumbnailGeneration 모델 - 썸네일 생성 세션 관리

사용자의 썸네일 생성 세션 전체를 저장하고 관리합니다.
키워드 선택, 제목 세트 생성, 썸네일 생성, 최종 선택까지의 모든 과정과
중간 결과물을 포함합니다.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from app.core.db import Base


class ThumbnailGeneration(Base):
    """
    썸네일 생성 세션 테이블
    
    사용자가 썸네일 생성을 시작하면 하나의 세션이 생성되며,
    전체 프로세스(키워드 추출 → 제목 생성 → 썸네일 생성)의
    모든 중간 결과와 최종 선택 정보를 저장합니다.
    
    Attributes:
        id: 세션 고유 ID (session_id)
        user_id: 생성한 사용자 UUID
        verified_script_id: 기반이 된 검증된 스크립트 ID (선택사항)
        video_title: 영상 제목 (사용자 입력 또는 스크립트에서 추출)
        youtube_video_id: 유튜브 업로드 후 입력 (선택사항)
        youtube_video_url: 유튜브 영상 URL (선택사항)
        script_summary: 스크립트 요약 (선택사항)
        script_chunks: 키워드 기반 청킹된 스크립트 (JSON)
        image_refs: 사용자가 업로드한 이미지 레퍼런스 S3 URL (JSON)
        selected_keywords: 사용자가 선택한 키워드 리스트
        selected_title_idx: 선택된 제목 세트 인덱스 (0-2)
        selected_thumbnail_idx: 선택된 썸네일 인덱스 (0-2)
        title_sets: 생성된 제목 세트 3개 (JSON)
        thumbnails: 생성된 썸네일 3개 (JSON, 다운로드 정보 포함)
        regeneration_count: 썸네일 재생성 횟수
        status: 세션 상태 (processing/completed/failed/cancelled)
        created_at: 세션 생성 시각
        completed_at: 세션 완료 시각
    """
    __tablename__ = "thumbnail_generations"
    
    # --- 기본 정보 ---
    id = Column(String(255), primary_key=True)
    # 세션 고유 ID (UUID 형식 문자열)
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # 생성한 사용자 (기존 users 테이블 참조)
    
    # --- 외부 참조 (FK 없이 ID만 저장) ---
    verified_script_id = Column(String(255), nullable=True)
    # 기반이 된 검증된 스크립트 ID (VERIFIED_SCRIPTS 테이블, 나중에 FK 추가 가능)
    
    video_title = Column(String(200), nullable=True)
    # 영상 제목 (사용자 입력 또는 스크립트에서 자동 추출)
    
    youtube_video_id = Column(String(50), nullable=True)
    # 유튜브 영상 ID (예: "dQw4w9WgXcQ", 업로드 후 입력)
    
    youtube_video_url = Column(String(500), nullable=True)
    # 유튜브 영상 전체 URL (예: "https://youtu.be/dQw4w9WgXcQ")
    
    # --- 입력 데이터 ---
    script_summary = Column(String(500), nullable=True)
    # 스크립트 요약 (Copywriter, VisualDirector가 사용)
    # 예: "2026년 AI 반도체 시장의 급성장과 삼성/SK하이닉스의 경쟁 구도 분석"
    
    script_chunks = Column(JSON, nullable=False)
    # 키워드 기반으로 청킹된 스크립트 리스트
    # [
    #   {
    #     "idx": 0,
    #     "title": "AI 반도체 시장 개요",
    #     "content": "최근 AI 반도체 시장이 급성장하고 있습니다...",
    #     "keywords": ["AI 반도체", "시장"],
    #     "word_count": 150
    #   },
    #   { "idx": 1, ... }
    # ]
    
    image_refs = Column(JSON, nullable=False)
    # 사용자가 업로드한 이미지 레퍼런스 (S3 URL)
    # {
    #   "person": "s3://bucket/user_uploads/user_123/session_456_person.jpg",
    #   "layout": "s3://bucket/user_uploads/user_123/session_456_layout.jpg",
    #   "asset": "s3://bucket/user_uploads/user_123/session_456_asset.png",
    #   "style": null  (선택사항)
    # }
    
    # --- 사용자 선택 정보 ---
    selected_keywords = Column(JSON, nullable=False)
    # 사용자가 선택한 키워드 리스트
    # 예: ["AI 반도체", "삼성전자", "HBM 메모리"]
    
    selected_title_idx = Column(Integer, nullable=False)
    # 선택된 제목 세트 인덱스 (0, 1, 2 중 하나)
    
    selected_thumbnail_idx = Column(Integer, nullable=False)
    # 선택된 썸네일 인덱스 (0, 1, 2 중 하나)
    
    # --- 생성 결과 (JSON) ---
    title_sets = Column(JSON, nullable=False)
    # 생성된 제목 세트 3개
    # [
    #   {
    #     "id": 0,
    #     "main_title": "AI 반도체 전쟁의 승자는?",
    #     "sub_title": "삼성 vs SK하이닉스 완벽 분석",
    #     "rationale": "호기심 자극 + 경쟁 구도 강조",
    #     "hook_type": "curiosity_gap"
    #   },
    #   { "id": 1, ... },
    #   { "id": 2, ... }
    # ]
    
    thumbnails = Column(JSON, nullable=False)
    # 생성된 썸네일 3개 (다운로드 정보 포함)
    # [
    #   {
    #     "id": 0,
    #     "image_url": "s3://bucket/thumbnails/session_123/0.png",
    #     "image_key": "thumbnails/session_123/0.png",
    #     "strategy_id": "curiosity_gap",
    #     "strategy_name": "호기심 자극형",
    #     "thumbnail_type": "A",
    #     "style_name": "강렬한 임팩트",
    #     "prompt_used": "A bold, high-impact thumbnail...",
    #     "downloaded": false,
    #     "downloaded_at": null
    #   },
    #   { "id": 1, ... },
    #   { "id": 2, ... }
    # ]
    
    # --- 메타데이터 ---
    regeneration_count = Column(Integer, default=0, nullable=False)
    # 썸네일 재생성 횟수 (최대 1회 제한)
    
    status = Column(String(50), default="processing", nullable=False)
    # 세션 상태:
    # - "processing": 진행 중
    # - "completed": 완료 (썸네일 생성 + 선택 완료)
    # - "failed": 실패 (에러 발생)
    # - "cancelled": 취소 (사용자가 중단)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    # 세션 생성 시각
    
    completed_at = Column(DateTime, nullable=True)
    # 세션 완료 시각 (completed/failed/cancelled 시 기록)
    
    # --- Relationships ---
    user = relationship("User", back_populates="thumbnail_generations")
    # 생성한 사용자
    
    def __repr__(self):
        return f"<ThumbnailGeneration(id={self.id}, status={self.status}, user_id={self.user_id})>"
    
    def get_selected_title(self):
        """선택된 제목 세트 반환"""
        if self.title_sets and 0 <= self.selected_title_idx < len(self.title_sets):
            return self.title_sets[self.selected_title_idx]
        return None
    
    def get_selected_thumbnail(self):
        """선택된 썸네일 반환"""
        if self.thumbnails and 0 <= self.selected_thumbnail_idx < len(self.thumbnails):
            return self.thumbnails[self.selected_thumbnail_idx]
        return None
    
    def mark_thumbnail_downloaded(self, thumbnail_idx: int):
        """
        썸네일 다운로드 상태 업데이트
        
        Args:
            thumbnail_idx: 다운로드한 썸네일 인덱스 (0-2)
        """
        if self.thumbnails and 0 <= thumbnail_idx < len(self.thumbnails):
            self.thumbnails[thumbnail_idx]["downloaded"] = True
            self.thumbnails[thumbnail_idx]["downloaded_at"] = datetime.utcnow().isoformat()
