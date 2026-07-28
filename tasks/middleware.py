"""
OverdueTaskMiddleware
─────────────────────
Automatically flips any non-completed task whose due_date has passed
to status='overdue' on the first authenticated request of each calendar
day. The check is throttled to once per day (per server process) using a
module-level sentinel date, so it never adds meaningful latency.
"""

from django.utils import timezone

# Module-level sentinel — stores the last date the sweep was run.
# Resets automatically when the server restarts or a new day arrives.
_last_sweep_date = None


class OverdueTaskMiddleware:
    """
    Lightweight middleware that keeps task statuses current without
    requiring Celery, cron, or any external scheduler.
    """

    ACTIVE_STATUSES = [
        'not_started', 'processing', 'to_advisers',
        'accounting', 'oca', 'osas', 'ppss', 'supply',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._sweep_if_needed(request)
        return self.get_response(request)

    def _sweep_if_needed(self, request):
        """Run the overdue sweep at most once per calendar day."""
        global _last_sweep_date

        # Only run for authenticated users (avoids DB hit on login page etc.)
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return

        today = timezone.localdate()

        if _last_sweep_date == today:
            return  # Already swept today — skip

        try:
            from tasks.models import Task
            updated = Task.objects.filter(
                due_date__lt=today,
                status__in=self.ACTIVE_STATUSES,
                is_archived=False,
            ).update(status='overdue')

            _last_sweep_date = today

            if updated:
                import logging
                logging.getLogger('tasks').info(
                    f"[OverdueTaskMiddleware] Marked {updated} task(s) as overdue on {today}."
                )
        except Exception:
            # Never crash the request pipeline due to overdue sweep failure
            pass
