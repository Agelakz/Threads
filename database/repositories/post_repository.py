from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import ThreadPost

class PostRepository:
    """Repository handling CRUD operations for ThreadPost."""
    
    def __init__(self, db_session: Session):
        self.db = db_session

    def create(self, post_data: dict) -> ThreadPost:
        """Create a new post record."""
        post = ThreadPost(**post_data)
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return post

    def get_by_post_id(self, post_id: str) -> Optional[ThreadPost]:
        """Fetch a post by its unique Threads post_id."""
        return self.db.query(ThreadPost).filter(ThreadPost.post_id == post_id).first()

    def get_unprocessed_posts(self, limit: int = 10) -> List[ThreadPost]:
        """Fetch posts that haven't been processed by the AI layer."""
        return self.db.query(ThreadPost).filter(ThreadPost.is_processed == False).limit(limit).all()

    def update(self, post_id: str, update_data: dict) -> Optional[ThreadPost]:
        """Update fields of an existing post."""
        post = self.get_by_post_id(post_id)
        if post:
            for key, value in update_data.items():
                if hasattr(post, key):
                    setattr(post, key, value)
            self.db.commit()
            self.db.refresh(post)
        return post

    def mark_as_processed(self, post_id: str) -> bool:
        """Flag a post as successfully processed."""
        post = self.get_by_post_id(post_id)
        if post:
            post.is_processed = True
            self.db.commit()
            return True
        return False

    def delete(self, post_id: str) -> bool:
        """Delete a post from the database."""
        post = self.get_by_post_id(post_id)
        if post:
            self.db.delete(post)
            self.db.commit()
            return True
        return False
