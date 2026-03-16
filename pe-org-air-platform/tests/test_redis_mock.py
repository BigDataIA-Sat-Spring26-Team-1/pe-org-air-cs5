
import pytest
from unittest.mock import MagicMock, patch
from app.services.redis_cache import RedisCache
from pydantic import BaseModel

class SmallModel(BaseModel):
    id: int
    name: str

def test_cache_get_set_operations():
    mock_redis = MagicMock()
    with patch('redis.Redis', return_value=mock_redis):
        cache = RedisCache("localhost", 6379)
        val = SmallModel(id=1, name="test")
        
        cache.set("test_key", val, ttl_seconds=60)
        mock_redis.setex.assert_called()
        
        mock_redis.get.return_value = val.model_dump_json()
        result = cache.get("test_key", SmallModel)
        assert result.id == 1
        assert result.name == "test"

def test_cache_delete_operation():
    mock_redis = MagicMock()
    with patch('redis.Redis', return_value=mock_redis):
        cache = RedisCache("localhost", 6379)
        cache.delete("test_key")
        mock_redis.delete.assert_called_with("test_key")
