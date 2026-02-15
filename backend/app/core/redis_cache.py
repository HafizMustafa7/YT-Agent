"""
Redis cache service for trending videos.
Provides caching with TTL, statistics, and management functions.
"""
import json
import redis
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.config.settings import settings


class RedisCache:
    """Redis-based cache with TTL support for Redis Cloud."""
    
    def __init__(self):
        """Initialize Redis connection pool."""
        self.enabled = settings.REDIS_ENABLED
        self.ttl = settings.REDIS_TTL_SECONDS
        self.key_prefix = settings.REDIS_KEY_PREFIX
        
        if self.enabled:
            try:
                # Redis Cloud connection with SSL support
                connection_params = {
                    "host": settings.REDIS_HOST,
                    "port": settings.REDIS_PORT,
                    "password": settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                    "db": settings.REDIS_DB,
                    "decode_responses": True,
                    "max_connections": settings.REDIS_MAX_CONNECTIONS,
                    "socket_timeout": settings.REDIS_SOCKET_TIMEOUT,
                    "socket_connect_timeout": settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                }
                
                # Try with SSL first if enabled
                if settings.REDIS_SSL:
                    try:
                        import ssl
                        connection_params["ssl"] = True
                        connection_params["ssl_cert_reqs"] = ssl.CERT_NONE
                        self.client = redis.Redis(**connection_params)
                        self.client.ping()
                        print(f"✅ Redis connected successfully (SSL) to {settings.REDIS_HOST}:{settings.REDIS_PORT}")
                    except Exception as ssl_error:
                        print(f"⚠️  SSL connection failed: {ssl_error}")
                        print(f"🔄 Retrying without SSL...")
                        # Retry without SSL
                        connection_params.pop("ssl", None)
                        connection_params.pop("ssl_cert_reqs", None)
                        self.client = redis.Redis(**connection_params)
                        self.client.ping()
                        print(f"✅ Redis connected successfully (non-SSL) to {settings.REDIS_HOST}:{settings.REDIS_PORT}")
                else:
                    # Connect without SSL
                    self.client = redis.Redis(**connection_params)
                    self.client.ping()
                    print(f"✅ Redis connected successfully to {settings.REDIS_HOST}:{settings.REDIS_PORT}")
                
                print(f"⏱️  Cache TTL: {self.ttl} seconds ({self.ttl/3600} hours)")
            except redis.ConnectionError as e:
                print(f"❌ Redis connection failed: {e}")
                self.enabled = False
                self.client = None
        else:
            self.client = None
            print("ℹ️  Redis caching disabled")
    
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
                print(f"⚠️  Redis get timeout/connection error for {key}: {timeout_error}")
                # Try to reconnect once
                try:
                    self.client.ping()
                    # Retry once after ping
                    data = self.client.get(cache_key)
                except Exception as reconnect_error:
                    print(f"⚠️  Redis reconnection failed: {reconnect_error}")
                    return None
            
            if data:
                # Increment hit counter (non-critical, don't fail if this fails)
                try:
                    self.client.incr(f"{self.key_prefix}stats:hits")
                except:
                    pass  # Stats are non-critical
                print(f"✅ Cache HIT: {key}")
                return json.loads(data)
            else:
                # Increment miss counter (non-critical, don't fail if this fails)
                try:
                    self.client.incr(f"{self.key_prefix}stats:misses")
                except:
                    pass  # Stats are non-critical
                print(f"❌ Cache MISS: {key}")
                return None
                
        except Exception as e:
            print(f"Redis get error: {e}")
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
                print(f"⚠️  Redis set timeout/connection error for {key}: {timeout_error}")
                # Try to reconnect once
                try:
                    self.client.ping()
                except:
                    print(f"⚠️  Redis reconnection failed, disabling cache for this operation")
                    return False
                # Retry once after ping
                try:
                    self.client.setex(
                        cache_key,
                        ttl,
                        json.dumps(data, default=str)
                    )
                except Exception as retry_error:
                    print(f"Redis set retry failed: {retry_error}")
                    return False
            
            # Track cache metadata (non-critical, don't fail if this fails)
            try:
                metadata_key = f"{cache_key}:metadata"
                metadata = {
                    "created_at": datetime.now().isoformat(),
                    "ttl": ttl,
                    "expires_at": datetime.now().timestamp() + ttl
                }
                self.client.setex(metadata_key, ttl, json.dumps(metadata))
            except Exception as metadata_error:
                # Metadata is non-critical, just log and continue
                print(f"⚠️  Redis metadata set failed (non-critical): {metadata_error}")
            
            print(f"💾 Cached: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            print(f"Redis set error: {e}")
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
            print(f"🗑️  Deleted cache: {key}")
            return True
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all cache entries with our prefix."""
        if not self.enabled or not self.client:
            return False
        
        try:
            # Find all keys with our prefix
            pattern = f"{self.key_prefix}*"
            keys = self.client.keys(pattern)
            
            if keys:
                self.client.delete(*keys)
                print(f"🧹 Cleared {len(keys)} cache entries")
            
            return True
        except Exception as e:
            print(f"Redis clear error: {e}")
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
            cached_items = len(self.client.keys(pattern))
            
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
            keys = self.client.keys(pattern)
            # Remove prefix from keys
            return [key.replace(self.key_prefix, "") for key in keys]
        except Exception as e:
            print(f"Redis keys error: {e}")
            return []


# Global cache instance
redis_cache = RedisCache()
