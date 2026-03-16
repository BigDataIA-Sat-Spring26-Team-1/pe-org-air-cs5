import redis
from typing import Optional, TypeVar, Type, List
from pydantic import BaseModel
from app.config import settings

T = TypeVar('T', bound=BaseModel)

class RedisCache:
    def __init__(self, host: str, port: int, db: int = 0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def get(self, key: str, model: Type[T]) -> Optional[T]:
        """Get cached item, deserialize to Pydantic model."""
        try:
            data = self.client.get(key)
            if data:
                return model.model_validate_json(data)
        except Exception:
            pass
        return None

    def get_list(self, key: str, model: Type[T]) -> Optional[List[T]]:
        """Get cached list of Pydantic models."""
        try:
            import json
            data = self.client.get(key)
            if data:
                items = json.loads(data)
                return [model.model_validate(item) for item in items]
        except Exception:
            pass
        return None

    def set(self, key: str, value: BaseModel, ttl_seconds: int) -> None:
        """Cache Pydantic model with TTL."""
        try:
            self.client.setex(
                key,
                ttl_seconds,
                value.model_dump_json()
            )
        except Exception:
            pass

    def set_list(self, key: str, value: List[BaseModel], ttl_seconds: int) -> None:
        """Cache list of Pydantic models with TTL."""
        try:
            import json
            serialized = json.dumps([v.model_dump() for v in value], default=str)
            self.client.setex(key, ttl_seconds, serialized)
        except Exception:
            pass

    def delete(self, key: str) -> None:
        """Invalidate cache entry."""
        try:
            self.client.delete(key)
        except Exception:
            pass

    def delete_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching pattern."""
        try:
            for key in self.client.scan_iter(match=pattern):
                self.client.delete(key)
        except Exception:
            pass

# Initialize global cache instance
cache = RedisCache(
    host=settings.REDIS_HOST, 
    port=settings.REDIS_PORT, 
    db=settings.REDIS_DB
)