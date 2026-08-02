"""Cache key families — TOOLS.md section 6's "every key family has a
prefix and version" and "TTLs are explicit". `CACHE_VERSION` bumps
whenever a cached value's shape changes, invalidating every existing key
for free (old-version keys simply expire and are never read again).
"""

CACHE_VERSION = "v1"
_NAMESPACE = "crm"

# Seconds. Deliberately short for anything permission-sensitive
# (analytics/dashboard/permissions) so a role or data change is visible
# quickly; longer for read-mostly configuration (settings).
CACHE_TTL_SECONDS: dict[str, int] = {
    "analytics": 60,
    "permissions": 300,
    "dashboard": 60,
    "reports": 120,
    "settings": 120,
    "customer_summary": 90,
}


def build_key(family: str, *parts: str) -> str:
    if family not in CACHE_TTL_SECONDS:
        raise ValueError(f"Unknown cache key family: {family!r}")
    joined = ":".join(str(p) for p in parts)
    return f"{_NAMESPACE}:{CACHE_VERSION}:{family}:{joined}"


def build_prefix(family: str, *parts: str) -> str:
    """A key prefix suitable for `SCAN`-based bulk invalidation of an
    entire family or sub-family (`app.cache.service.invalidate_prefix`)."""
    return build_key(family, *parts) if parts else f"{_NAMESPACE}:{CACHE_VERSION}:{family}"
