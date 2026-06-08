import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import config
from database.models import Base

# Get Database URL
db_url = config.DATABASE_URL

# Auto-create directory if using a relative SQLite file
if db_url.startswith("sqlite:///"):
    db_path = db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

# Create SQLAlchemy engine
engine = create_engine(
    db_url, 
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)
    
    # Auto-migrate existing data for Status Management feature
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            # Add status column if it doesn't exist
            conn.execute(text("ALTER TABLE thread_posts ADD COLUMN status VARCHAR(20) DEFAULT 'PENDING'"))
            conn.commit()
            
            # Migrate old records to PENDING where status is null
            conn.execute(text("UPDATE thread_posts SET status = 'PENDING' WHERE status IS NULL"))
            conn.commit()
        except Exception:
            # Column already exists, safe to ignore
            pass

def get_db():
    """Dependency for getting a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
