"""
Safe LLM response cache manager.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any

from .cache_key_builder import build_cache_key
from .cache_metrics import CacheMetrics
from .eviction_policy import (
    EvictionPolicy,
    CacheInvalidator,
    find_and_remove_oldest,
    invalidate_all,
    invalidate_by_session,
    remove_entry,
)
from .guardrails import (
    CacheEligibilityDecision,
    evaluate_transcript_eligibility,
    evaluate_response_eligibility,
)
from .models import CachedResponseEntry
from .response_cache_logic.persistence import persist_cache, load_cache


class LLMResponseCache:
    """TTL-based response cache manager."""

    def __init__(
        self,
        *,
        ttl_seconds: int = 180,
        max_entries: int = 256,
        min_chars: int = 24,
        persistence_path: Path | None = None,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.min_chars = min_chars
        self.persistence_path = persistence_path

        self._entries: dict[str, CachedResponseEntry] = {}
        self._session_index: dict[str, set[str]] = {}

        self._metrics = CacheMetrics()
        self._eviction_policy = EvictionPolicy(ttl_seconds, max_entries)
        self._invalidator = CacheInvalidator()

        if self.persistence_path:
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            load_cache(self)

    @property
    def estimated_latency_saved_ms(self) -> float:
        return self._metrics.estimated_latency_saved_ms

    def _now_epoch(self) -> float:
        return time.time()

    def _iso_from_epoch(self, value: float) -> str:
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()

    def record_skip(self, reason: str) -> None:
        self._metrics.record_skip(reason)

    def build_key(self, **kwargs) -> tuple[str, str, str]:
        return build_cache_key(**kwargs)

    def evaluate_eligibility(self, **kwargs) -> CacheEligibilityDecision:
        return evaluate_transcript_eligibility(**kwargs)

    def lookup(self, key: str) -> str | None:
        self._metrics.record_lookup()
        entry = self._entries.get(key)
        if not entry:
            self._metrics.record_miss()
            return None

        if self._now_epoch() >= entry.expires_at_epoch:
            self._metrics.record_stale()
            self._metrics.record_miss()
            remove_entry(self._entries, self._session_index, key, count_invalidation=False)
            return None

        self._metrics.record_hit(entry.source_latency_ms)
        return entry.response_text

    def should_store_response(self, text: str) -> CacheEligibilityDecision:
        return evaluate_response_eligibility(text, self.min_chars)

    def store(self, **kwargs) -> None:
        now = self._now_epoch()
        expiry = self._eviction_policy.calculate_expiry(now)
        key = kwargs["key"]

        entry = CachedResponseEntry(
            created_at_epoch=now,
            expires_at_epoch=expiry,
            created_at_utc=self._iso_from_epoch(now),
            expires_at_utc=self._iso_from_epoch(expiry),
            **kwargs
        )

        remove_entry(self._entries, self._session_index, key, count_invalidation=False)
        self._entries[key] = entry
        self._session_index.setdefault(kwargs["session_id"], set()).add(key)
        self._metrics.record_write()
        self._evict_if_needed()
        persist_cache(self)

    def _evict_if_needed(self) -> None:
        while self._eviction_policy.should_evict(len(self._entries)):
            if find_and_remove_oldest(self._entries, self._session_index):
                self._eviction_policy.record_eviction()

    def invalidate_session(self, session_id: str) -> None:
        removed = invalidate_by_session(self._entries, self._session_index, session_id)
        if removed > 0:
            self._metrics.record_invalidation_batch(removed)
            persist_cache(self)

    def invalidate_all(self) -> None:
        removed = invalidate_all(self._entries, self._session_index)
        if removed > 0:
            self._metrics.record_invalidation_batch(removed)
            persist_cache(self)

    def get_stats(self) -> dict[str, Any]:
        return self._metrics.get_all_stats(self.ttl_seconds, self.max_entries, len(self._entries))
