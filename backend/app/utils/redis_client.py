import os
import logging
from typing import Optional
import redis
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv()
logger = logging.getLogger(__name__)

# Standard Redis Connection URL
# Examples:
#   Local Docker: "redis://localhost:6379/0"
#   Hosted / Cloud (Upstash, AWS ElastiCache, Redis Cloud): "rediss://default:password@xyz.upstash.io:6379"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_pool: Optional[redis.ConnectionPool] = None
_client: Optional[redis.Redis] = None


def get_redis_pool() -> redis.ConnectionPool:
    global _pool
    if _pool is None:
        try:
            # from_url handles both redis:// and secure rediss:// (TLS), auth, DB indices
            _pool = redis.ConnectionPool.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
                retry_on_timeout=False,
                max_connections=20
            )
            logger.info("Initialized Redis connection pool for: %s", REDIS_URL.split("@")[-1])
        except Exception as e:
            logger.warning("Failed to initialize Redis pool (%s): %s", REDIS_URL, e)
            _pool = None
            return None
    return _pool


def get_redis_client() -> Optional[redis.Redis]:
    """
    Returns a configured Redis client.
    Returns None if connection to Redis fails, allowing calling code to handle fallbacks gracefully.
    """
    global _client
    try:
        if _client is None:
            pool = get_redis_pool()
            if pool is None:
                return None
            _client = redis.Redis(connection_pool=pool)
        
        # Test connection with a quick ping
        _client.ping()
        return _client
    except Exception as e:
        logger.debug("Redis connection ping failed (%s): %s", REDIS_URL.split("@")[-1], e)
        _client = None
        return None


def is_redis_available() -> bool:
    """Checks if Redis server is currently responding."""
    try:
        client = get_redis_client()
        return client is not None
    except Exception:
        return False
