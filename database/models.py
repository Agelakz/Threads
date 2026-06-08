from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class ThreadPost(Base):
    """Model for storing scraped Threads posts."""
    __tablename__ = 'thread_posts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(255), unique=True, index=True, nullable=False)
    author_username = Column(String(255))
    content = Column(Text)
    url = Column(String(500))
    keyword = Column(String(255))
    scraped_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Status tracking for downstream AI & Matcher processing
    status = Column(String(20), default="PENDING")
    is_processed = Column(Boolean, default=False) # Legacy flag
    intent_score = Column(Integer, nullable=True)
    category = Column(String(100), nullable=True)
    reply_draft = Column(Text, nullable=True)

class SystemLog(Base):
    """Model for storing application execution logs."""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(50)) # e.g., INFO, WARNING, ERROR
    module = Column(String(100)) # e.g., SessionManager, ThreadsMonitor
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class AffiliateLink(Base):
    """Model for storing original product URLs and their Shopee Affiliate short links."""
    __tablename__ = 'affiliate_links'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_url = Column(String(500), unique=True, index=True, nullable=False)
    affiliate_url = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ProductMetric(Base):
    """Model for storing Product Ranking metrics."""
    __tablename__ = 'product_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(500), index=True)
    category = Column(String(100))
    click_count = Column(Integer, default=0)
    conversion_count = Column(Integer, default=0)
    product_score = Column(Integer, default=0)
    last_update = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
