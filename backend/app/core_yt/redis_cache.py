"""
Redis cache service for trending videos.
Provides caching with TTL, statistics, and management functions.
"""
import json
import logging
import redis
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-based cache with TTL support for Redis Cloud."""
    
    def __init__(self):
        """Initialize Redis connection pool."""
        self.enabled = settings.REDIS_ENABLED
        self.ttl = settings.REDIS_TTL_SECONDS
        self.key_prefix = settings.REDIS_KEY_PREFIX
        
        if self.enabled:
            try:
                # Common connection params
                common_params = {
                    "decode_responses": True,
                    "max_connections": settings.REDIS_MAX_CONNECTIONS,
                    "socket_timeout": settings.REDIS_SOCKET_TIMEOUT,
                    "socket_connect_timeout": settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                }

                if settings.REDIS_URL:
                    # Initialize from URL (e.g., Render)
                    self.client = redis.Redis.from_url(settings.REDIS_URL, **common_params)
                    self.client.ping()
                    logger.info("Redis connected successfully via REDIS_URL")
                else:
                    # Fallback to host/port (e.g., local or Redis Cloud)
                    connection_params = {
                        "host": settings.REDIS_HOST,
                        "port": settings.REDIS_PORT,
                        "password": settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                        "db": settings.REDIS_DB,
                        **common_params
                    }
                    
                    # Try with SSL first if enabled
                    if settings.REDIS_SSL:
                        import ssl
                        connection_params["ssl"] = True
                        connection_params["ssl_cert_reqs"] = ssl.CERT_NONE
                        self.client = redis.Redis(**connection_params)
                        self.client.ping()
                        logger.info("Redis connected successfully (SSL) to %s:%s", settings.REDIS_HOST, settings.REDIS_PORT)
                    else:
                        # Connect without SSL
                        self.client = redis.Redis(**connection_params)
                        self.client.ping()
                        logger.info("Redis connected successfully to %s:%s", settings.REDIS_HOST, settings.REDIS_PORT)
                
                logger.info("Cache TTL: %ds (%.1f hours)", self.ttl, self.ttl / 3600)
            except redis.ConnectionError as e:
                logger.error("Redis connection failed: %s", e)
                self.enabled = False
                self.client = None
        else:
            self.client = None
            logger.info("Redis caching disabled")
    
    def _make_key(self, key: str) -> str:
        """Generate prefixed cache key."""
        return f"{self.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached data.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            cache_key = self._make_key(key)
            try:
                data = self.client.get(cache_key)
            except (redis.TimeoutError, redis.ConnectionError, OSError) as timeout_error:
                logger.warning("Redis get timeout/connection error for %s: %s", key, timeout_error)
                # Try to reconnect once
                try:
                    self.client.ping()
                    # Retry once after ping
                    data = self.client.get(cache_key)
                except Exception as reconnect_error:
                    logger.warning("Redis reconnection failed: %s", reconnect_error)
                    return None
            
            if data:
                # Increment hit counter (non-critical, don't fail if this fails)
                try:
                    self.client.incr(f"{self.key_prefix}stats:hits")
                except Exception:
                    pass  # Stats are non-critical
                logger.debug("Cache HIT: %s", key)
                return json.loads(data)
            else:
                # Increment miss counter (non-critical, don't fail if this fails)
                try:
                    self.client.incr(f"{self.key_prefix}stats:misses")
                except Exception:
                    pass  # Stats are non-critical
                logger.debug("Cache MISS: %s", key)
                return None
                
        except Exception as e:
            logger.warning("Redis get error: %s", e)
            # Don't fail the entire request if cache fails
            return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """
        Store data in cache with TTL.
        
        Args:
            key: Cache key
            data: Data to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (default: from settings)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            cache_key = self._make_key(key)
            ttl = ttl or self.ttl
            
            # Store data with TTL (with timeout handling)
            try:
                self.client.setex(
                    cache_key,
                    ttl,
                    json.dumps(data, default=str)
                )
            except (redis.TimeoutError, redis.ConnectionError, OSError) as timeout_error:
                logger.warning("Redis set timeout/connection error for %s: %s", key, timeout_error)
                # Try to reconnect once
                try:
                    self.client.ping()
                except Exception:
                    logger.warning("Redis reconnection failed, disabling cache for this operation")
                    return False
                # Retry once after ping
                try:
                    self.client.setex(
                        cache_key,
                        ttl,
                        json.dumps(data, default=str)
                    )
                except Exception as retry_error:
                    logger.warning("Redis set retry failed: %s", retry_error)
                    return False
            
            # Track cache metadata (non-critical, don't fail if this fails)
            try:
                metadata_key = f"{cache_key}:metadata"
                metadata = {
                    "created_at": datetime.now().isoformat(),
                    "ttl": ttl
                }
                self.client.setex(metadata_key, ttl, json.dumps(metadata))
            except Exception as metadata_error:
                logger.debug("Redis metadata set failed (non-critical): %s", metadata_error)
            
            logger.debug("Cached: %s (TTL: %ds)", key, ttl)
            return True
            
        except Exception as e:
            logger.warning("Redis set error: %s", e)
            # Don't fail the entire request if caching fails
            return False
    
    def delete(self, key: str) -> bool:
        """Delete specific cache entry."""
        if not self.enabled or not self.client:
            return False
        
        try:
            cache_key = self._make_key(key)
            self.client.delete(cache_key)
            self.client.delete(f"{cache_key}:metadata")
            logger.info("Deleted cache: %s", key)
            return True
        except Exception as e:
            logger.warning("Redis delete error: %s", e)
            return False
    
    def clear_all(self) -> bool:
        """Clear all cache entries with our prefix."""
        if not self.enabled or not self.client:
            return False
        
        try:
            # Find all keys with our prefix
            pattern = f"{self.key_prefix}*"
            keys = list(self.client.scan_iter(match=pattern))
            
            if keys:
                self.client.delete(*keys)
                logger.info("Cleared %d cache entries", len(keys))
            
            return True
        except Exception as e:
            logger.warning("Redis clear error: %s", e)
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled or not self.client:
            return {
                "enabled": False,
                "message": "Redis caching is disabled"
            }
        
        try:
            hits = int(self.client.get(f"{self.key_prefix}stats:hits") or 0)
            misses = int(self.client.get(f"{self.key_prefix}stats:misses") or 0)
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            # Count cached items
            pattern = f"{self.key_prefix}trends_*"
            cached_items = len(list(self.client.scan_iter(match=pattern)))
            
            # Get Redis info
            info = self.client.info()
            
            return {
                "enabled": True,
                "hits": hits,
                "misses": misses,
                "total_requests": total,
                "hit_rate": round(hit_rate, 2),
                "cached_items": cached_items,
                "ttl_seconds": self.ttl,
                "ttl_hours": round(self.ttl / 3600, 2),
                "redis_host": settings.REDIS_HOST,
                "redis_port": settings.REDIS_PORT,
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
            }
        except Exception as e:
            return {
                "enabled": True,
                "error": str(e)
            }
    
    def get_all_keys(self) -> List[str]:
        """Get all cache keys."""
        if not self.enabled or not self.client:
            return []
        
        try:
            pattern = f"{self.key_prefix}trends_*"
            keys = list(self.client.scan_iter(match=pattern))
            # Remove prefix from keys
            return [key.replace(self.key_prefix, "") for key in keys]
        except Exception as e:
            logger.warning("Redis keys error: %s", e)
            return []


# Global cache instance
redis_cache = RedisCache()
