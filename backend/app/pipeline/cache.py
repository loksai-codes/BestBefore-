import hashlib
import json
import os
import time
from typing import Any, Dict, Optional

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".cache")
CACHE_FILE = os.path.join(CACHE_DIR, "tavily_cache.json")
DEFAULT_TTL_SECONDS = 7200  # 2 hours


class TavilyCache:
    """In-memory + disk cache for Tavily API responses."""

    def __init__(self, ttl: int = DEFAULT_TTL_SECONDS) -> None:
        self.ttl = ttl
        self._memory: Dict[str, Dict[str, Any]] = {}
        self._load_disk()

    def _hash_key(self, prefix: str, key_data: Any) -> str:
        serialized = json.dumps(key_data, sort_keys=True)
        h = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"{prefix}:{h}"

    def _load_disk(self) -> None:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    now = time.time()
                    # Filter out expired items
                    self._memory = {
                        k: v
                        for k, v in data.items()
                        if isinstance(v, dict) and v.get("expires_at", 0) > now
                    }
            except Exception:
                self._memory = {}

    def _save_disk(self) -> None:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._memory, f, indent=2)
        except Exception:
            pass  # Non-fatal if disk write fails

    def get(self, prefix: str, key_data: Any) -> Optional[Any]:
        key = self._hash_key(prefix, key_data)
        item = self._memory.get(key)
        if not item:
            return None

        if item.get("expires_at", 0) < time.time():
            self._memory.pop(key, None)
            return None

        return item.get("payload")

    def set(self, prefix: str, key_data: Any, payload: Any) -> None:
        key = self._hash_key(prefix, key_data)
        self._memory[key] = {
            "payload": payload,
            "expires_at": time.time() + self.ttl,
        }
        self._save_disk()


tavily_cache = TavilyCache()
