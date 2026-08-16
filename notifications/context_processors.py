from django.core.cache import cache
from notifications.models import Notification


def notifications_processor(request):
    if request.user.is_authenticated:
        user_id = request.user.pk

        # Single cache key for all notification context data (TTL 30s)
        # Ensures zero DB queries on cache hit
        cache_key = f'notif_unread_{user_id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        unread_count = Notification.objects.filter(recipient_id=user_id, is_read=False).count()
        recent_notifications = list(
            Notification.objects.filter(recipient_id=user_id)
            .select_related('related_task')
            .only(
                'id', 'title', 'message', 'notification_type', 'is_read', 'created_at',
                'related_task__id', 'related_task__task_number'
            )[:5]
        )

        result = {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent_notifications,
        }
        cache.set(cache_key, result, 30)
        return result
    return {
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }
