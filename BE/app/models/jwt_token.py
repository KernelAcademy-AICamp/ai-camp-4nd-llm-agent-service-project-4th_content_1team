import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class JWTRefreshToken(Base):
    """JWT refresh token tracking model."""
    __tablename__ = "jwt_refresh_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jti = Column(String, unique=True, nullable=False, index=True)  # JWT ID
    
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # For token rotation tracking
    replaced_by_jti = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="jwt_refresh_tokens")
    
    # Indexes
    __table_args__ = (
        Index("ix_jwt_refresh_tokens_user_id", "user_id"),
        Index("ix_jwt_refresh_tokens_expires_at", "expires_at"),
    )
