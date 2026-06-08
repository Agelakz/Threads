from typing import List
from sqlalchemy.orm import Session
from database.models import SystemLog

class LogRepository:
    """Repository handling CRUD operations for SystemLog."""
    
    def __init__(self, db_session: Session):
        self.db = db_session

    def create(self, level: str, module: str, message: str) -> SystemLog:
        """Create a new system log entry."""
        log_entry = SystemLog(level=level, module=module, message=message)
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry

    def get_logs(self, limit: int = 50, level: str = None) -> List[SystemLog]:
        """Retrieve recent system logs, optionally filtered by level."""
        query = self.db.query(SystemLog)
        if level:
            query = query.filter(SystemLog.level == level)
        return query.order_by(SystemLog.created_at.desc()).limit(limit).all()

    def delete_old_logs(self, keep_latest: int = 1000) -> int:
        """Delete older logs to prevent the database from growing indefinitely."""
        # Find the IDs of the logs we want to keep
        logs_to_keep = self.db.query(SystemLog.id).order_by(SystemLog.created_at.desc()).limit(keep_latest).all()
        keep_ids = [log.id for log in logs_to_keep]
        
        # Delete logs that are NOT in the keep list
        deleted_count = self.db.query(SystemLog).filter(SystemLog.id.notin_(keep_ids)).delete(synchronize_session=False)
        self.db.commit()
        
        return deleted_count
