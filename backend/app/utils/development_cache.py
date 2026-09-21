import hashlib
import json
import logging
from typing import Optional, Any
from datetime import datetime, UTC

from .redis_client import get_redis_client

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "orbit:dev_cache:"
DEFAULT_CACHE_TTL = 7 * 24 * 3600  # 7 days


class WorkspaceDevelopmentCache:
    """
    High-performance Redis-backed cache for workspace developments and AI summaries.
    - Uses Redis as the primary persistent cache (works with local Docker Redis or cloud-hosted Redis via REDIS_URL).
    - Falls back to in-memory caching if Redis is temporarily unreachable.
    - Computes deterministic SHA256 fingerprints of development activities (commits, PRs, etc.).
    - When the fingerprint matches, serves the cached LLM synthesis with 0ms LLM latency and 0 API cost.
    """

    def __init__(self):
        # In-memory fallback dictionary: { workspace_id: { "fingerprint": str, "response": str, ... } }
        self._memory_fallback: dict[str, dict[str, Any]] = {}

    def _get_key(self, workspace_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}{workspace_id}"

    def compute_fingerprint(self, items: list[Any]) -> str:
        """
        Computes a deterministic SHA256 fingerprint representing the current state
        of developments (e.g. commit IDs, timestamps, PR numbers/states).
        """
        raw_parts = []
        for item in items:
            if hasattr(item, "__dict__"):
                # Object / SQLAlchemy model instance
                item_id = getattr(item, "id", getattr(item, "commit_sha", getattr(item, "pr_number", "")))
                item_time = getattr(
                    item,
                    "committed_at",
                    getattr(item, "updated_at", getattr(item, "created_at", ""))
                )
                item_state = getattr(item, "state", getattr(item, "status", getattr(item, "branch", "")))
                item_msg = getattr(item, "message", getattr(item, "title", ""))
                raw_parts.append(f"{item_id}:{item_time}:{item_state}:{item_msg}")
            elif isinstance(item, dict):
                item_id = item.get("id", item.get("commit_sha", item.get("pr_number", "")))
                item_time = item.get("committed_at", item.get("updated_at", item.get("created_at", "")))
                item_state = item.get("state", item.get("status", item.get("branch", "")))
                item_msg = item.get("message", item.get("title", ""))
                raw_parts.append(f"{item_id}:{item_time}:{item_state}:{item_msg}")
            else:
                raw_parts.append(str(item))

        serialized = "|".join(raw_parts)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get_cached_response(self, workspace_id: str, current_fingerprint: str) -> Optional[str]:
        """
        Returns the cached LLM synthesis if current developments match the cached fingerprint.
        Queries Redis first; falls back to in-memory cache if Redis is unavailable.
        """
        redis_client = get_redis_client()

        # 1. Try Redis
        if redis_client:
            try:
                raw = redis_client.get(self._get_key(workspace_id))
                if raw:
                    entry = json.loads(raw)
                    if entry.get("fingerprint") == current_fingerprint:
                        entry["hit_count"] = entry.get("hit_count", 0) + 1
                        # Update hit count asynchronously in Redis
                        try:
                            redis_client.setex(
                                self._get_key(workspace_id),
                                DEFAULT_CACHE_TTL,
                                json.dumps(entry)
                            )
                        except Exception:
                            pass

                        logger.info(
                            "Redis Development Cache HIT for workspace %s (fingerprint=%s, hits=%d). Skipping LLM.",
                            workspace_id,
                            current_fingerprint[:8],
                            entry["hit_count"]
                        )
                        resp = entry.get("response")
                        if isinstance(resp, list):
                            return "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in resp]).strip()
                        return str(resp) if resp is not None else None
                    else:
                        logger.info(
                            "Redis Development Cache INVALIDATED for workspace %s (new developments detected). Calling LLM.",
                            workspace_id
                        )
                        return None
            except Exception as e:
                logger.warning("Error reading from Redis cache: %s. Using memory fallback.", e)

        # 2. In-Memory Fallback
        entry = self._memory_fallback.get(workspace_id)
        if entry and entry.get("fingerprint") == current_fingerprint:
            entry["hit_count"] = entry.get("hit_count", 0) + 1
            logger.info(
                "Memory Fallback Cache HIT for workspace %s (fingerprint=%s). Skipping LLM.",
                workspace_id,
                current_fingerprint[:8]
            )
            resp = entry.get("response")
            if isinstance(resp, list):
                return "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in resp]).strip()
            return str(resp) if resp is not None else None

        return None

    def set_cached_response(self, workspace_id: str, fingerprint: str, response: Any) -> None:
        """
        Stores the LLM synthesis and development fingerprint in Redis (with TTL) and memory fallback.
        """
        if isinstance(response, list):
            clean_response = "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in response]).strip()
        else:
            clean_response = str(response or "").strip()

        payload = {
            "fingerprint": fingerprint,
            "response": clean_response,
            "updated_at": datetime.now(UTC).isoformat(),
            "hit_count": 0
        }

        # 1. Store in Redis
        redis_client = get_redis_client()
        if redis_client:
            try:
                redis_client.setex(
                    self._get_key(workspace_id),
                    DEFAULT_CACHE_TTL,
                    json.dumps(payload)
                )
                logger.info(
                    "Redis Development Cache STORED for workspace %s (fingerprint=%s, ttl=%ds)",
                    workspace_id,
                    fingerprint[:8],
                    DEFAULT_CACHE_TTL
                )
            except Exception as e:
                logger.warning("Failed to write to Redis: %s", e)

        # 2. Store in Memory Fallback
        self._memory_fallback[workspace_id] = payload

    def invalidate(self, workspace_id: str) -> None:
        """
        Explicitly invalidates the cache for a workspace across Redis and memory fallback.
        """
        redis_client = get_redis_client()
        if redis_client:
            try:
                redis_client.delete(self._get_key(workspace_id))
                logger.info("Redis Development Cache DELETED for workspace %s", workspace_id)
            except Exception as e:
                logger.warning("Failed to delete Redis key: %s", e)

        if workspace_id in self._memory_fallback:
            del self._memory_fallback[workspace_id]

    def get_status(self, workspace_id: str) -> dict[str, Any]:
        """
        Returns metadata about cache status and store type (Redis or Memory).
        """
        redis_client = get_redis_client()
        if redis_client:
            try:
                raw = redis_client.get(self._get_key(workspace_id))
                if raw:
                    entry = json.loads(raw)
                    return {
                        "cached": True,
                        "store": "redis",
                        "fingerprint": entry["fingerprint"][:8],
                        "updated_at": entry.get("updated_at"),
                        "hits": entry.get("hit_count", 0)
                    }
            except Exception:
                pass

        entry = self._memory_fallback.get(workspace_id)
        if entry:
            return {
                "cached": True,
                "store": "memory",
                "fingerprint": entry["fingerprint"][:8],
                "updated_at": entry.get("updated_at"),
                "hits": entry.get("hit_count", 0)
            }
        return {"cached": False, "store": "none"}


# Global singleton instance
development_cache = WorkspaceDevelopmentCache()
