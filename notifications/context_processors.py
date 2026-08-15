from django.core.cache import cache
from notifications.models import Notification


def notifications_processor(request):
    if request.user.is_authenticated:
        user_id = request.user.pk
        cache_key = f'notif_unread_{user_id}'
        unread_count = cache.get(cache_key)
        if unread_count is None:
            unread_count = Notification.objects.filter(recipient_id=user_id, is_read=False).count()
            cache.set(cache_key, unread_count, 30)  # Cache for 30 seconds

        recent_notifications = Notification.objects.filter(
            recipient_id=user_id
        ).select_related('related_task').only(
            'id', 'title', 'message', 'notification_type', 'is_read', 'created_at',
            'related_task__id', 'related_task__task_number'
        )[:5]
        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent_notifications,
        }
    return {
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }
