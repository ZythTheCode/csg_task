from django.core.cache import cache


def invalidate_task_caches(task):
    """Invalidate caches affected by a task mutation.

    Called after task create, update, delete, or status change to ensure
    stale cached data is purged for the task's organization and assigned officers.
    """
    org_id = task.organization_id
    if org_id:
        cache.delete(f'org_{org_id}_officers')

    # Invalidate notification caches for assigned officers
    try:
        assigned_ids = list(task.assigned_officers.values_list('id', flat=True))
    except Exception:
        assigned_ids = []
    for user_id in assigned_ids:
        cache.delete(f'notif_unread_{user_id}')

    # Invalidate dashboard chart caches for the task creator
    if task.created_by_id and org_id:
        cache.delete(f'dashboard_charts_{task.created_by_id}_{org_id}_all')
        cache.delete(f'dashboard_charts_{task.created_by_id}_{org_id}_my_tasks')
