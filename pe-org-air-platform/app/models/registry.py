from typing import Set
import structlog
from app.services.snowflake import db

logger = structlog.get_logger()

class DocumentRegistry:
    """
    Manages deduplication by checking existing content hashes in the database.
    """
    def __init__(self, initial_hashes: Set[str] = None):
        if initial_hashes is not None:
            self.known_hashes = initial_hashes
        else:
            self.known_hashes: Set[str] = set()
            self._refresh()

    def _refresh(self):
        """Reload all hashes from the documents table."""
        try:
            query = "SELECT content_hash FROM documents WHERE content_hash IS NOT NULL"
            rows = db.execute_query(query)
            self.known_hashes = {row['content_hash'] for row in rows}
            logger.info("registry_refreshed", count=len(self.known_hashes))
        except Exception as e:
            logger.warning("registry_refresh_failed", error=str(e), msg="Will start with empty registry")
            
    def is_processed(self, content_hash: str) -> bool:
        return content_hash in self.known_hashes

    def add(self, content_hash: str):
        self.known_hashes.add(content_hash)