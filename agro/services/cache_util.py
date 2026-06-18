"""Django cache helpers (shared across weather, market, chat rate limits)."""

from django.core.cache import cache


def cache_get(key: str):
    return cache.get(key)


def cache_set(key: str, value, ttl_seconds: int = 600) -> None:
    cache.set(key, value, timeout=ttl_seconds)
