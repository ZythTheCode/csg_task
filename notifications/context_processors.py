from core.cache_utils import safe_cache_get
from notifications.models import Notification


def notifications_processor(request):
    # Return immediately for unauthenticated users (zero queries)
    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0,
            'recent_notifications': [],
        }

    user_id = request.user.pk
    cache_key = f'notif_unread_{user_id}'

    def _fetch_notification_data():
        """Cold cache: execute COUNT + SELECT for recent notifications."""
        unread_count = Notification.objects.filter(
            recipient_id=user_id, is_read=False
        ).count()

        recent = list(
            Notification.objects.filter(
                recipient_id=user_id
            ).select_related('related_task').only(
                'id', 'title', 'notification_type', 'is_read', 'created_at',
                'related_task__id', 'related_task__task_number'
            ).order_by('-created_at')[:5]
        )

        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent,
        }

    # Warm cache: return cached value (zero queries)
    # Cold cache: execute COUNT + SELECT, cache with 30-second TTL
    return safe_cache_get(cache_key, _fetch_notification_data, timeout=30)
