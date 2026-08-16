from django.core.cache import cache
import logging

logger = logging.getLogger('csg.performance')


def safe_cache_get(key, fallback_fn, timeout=60):
    """
    Attempt cache read; on any failure, execute fallback_fn and cache result.
    Never raises to caller — always returns valid data.
    """
    try:
        value = cache.get(key)
        if value is not None:
            return value
    except Exception as e:
        logger.warning(f"Cache read failed for key={key}: {e}")

    value = fallback_fn()

    try:
        cache.set(key, value, timeout)
    except Exception as e:
        logger.warning(f"Cache write failed for key={key}: {e}")

    return value


def invalidate_task_caches(organization_id):
    """Invalidate all task-related caches for an organization."""
    cache.delete(f'officers_list_{organization_id}')
    # Dashboard count caches use a version key pattern.
    # Deleting the version key forces new cache keys on next read.
    cache.delete(f'dashboard_version_{organization_id}')


def get_dashboard_cache_key(user_id, scope, org_id):
    """Generate versioned dashboard cache key."""
    version = cache.get(f'dashboard_version_{org_id}', 0)
    return f'dashboard_counts_{user_id}_{scope}_v{version}'


def invalidate_officers_cache(organization_id):
    """Invalidate officers list cache for an organization."""
    cache.delete(f'officers_list_{organization_id}')
    cache.delete('officers_list_all')


def invalidate_org_cache():
    """Invalidate approved organizations cache."""
    cache.delete('approved_orgs_list')
