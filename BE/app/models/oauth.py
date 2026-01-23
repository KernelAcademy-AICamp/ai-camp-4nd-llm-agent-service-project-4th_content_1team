import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class OAuthAccount(Base):
    """OAuth account model for storing provider credentials."""
    __tablename__ = "oauth_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False, default="google")
    provider_account_id = Column(String, nullable=False)  # Google sub
    
    # OAuth tokens - TODO: Encrypt these in production
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    scope = Column(String, nullable=True)
    expires_at = Column(Integer, nullable=True)  # Unix timestamp
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="oauth_accounts")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("provider", "provider_account_id", name="uq_provider_account"),
        Index("ix_oauth_accounts_user_id", "user_id"),
    )
