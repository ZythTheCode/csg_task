"""
Query utility module with aggregate helper functions for performance optimization.

Each function uses Django ORM aggregation (conditional Count, TruncMonth, TruncDate)
instead of per-item loops to minimize database round-trips.
"""

from collections import defaultdict

from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone


def group_tasks_by_status(queryset, status_choices, limit_per_group=50):
    """
    Given a queryset of tasks with select_related/prefetch_related already applied,
    fetch all tasks and group them by status in Python.

    Returns:
        tuple: (grouped, counts) where
            grouped: dict[status_code] -> list[Task] (capped at limit_per_group)
            counts: dict[status_code] -> int (full count per status)
    """
    # Single aggregate query for counts grouped by status
    counts_qs = queryset.values('status').annotate(count=Count('id'))
    counts = {item['status']: item['count'] for item in counts_qs}

    # Fetch all tasks in a single query, ordered for consistent grouping
    all_tasks = list(queryset.order_by('status', '-created_at'))
    grouped = defaultdict(list)
    for task in all_tasks:
        if len(grouped[task.status]) < limit_per_group:
            grouped[task.status].append(task)

    return grouped, counts


def get_distributions(base_qs):
    """
    Single query for status + priority distributions using conditional Count.

    Returns a dict with keys like 'status_not_started', 'status_completed',
    'priority_low', 'priority_high', etc. — each mapping to an integer count.
    """
    from tasks.models import Task

    agg_kwargs = {}
    for code, label in Task.STATUS_CHOICES:
        agg_kwargs[f'status_{code}'] = Count('id', filter=Q(status=code))
    for code, label in Task.PRIORITY_CHOICES:
        agg_kwargs[f'priority_{code}'] = Count('id', filter=Q(priority=code))
    return base_qs.aggregate(**agg_kwargs)


def get_monthly_completed(base_qs, start_date):
    """
    Single query for monthly completed tasks using TruncMonth.

    Returns a queryset of dicts with 'month' (date) and 'count' (int) keys,
    ordered by month ascending.
    """
    return (
        base_qs
        .filter(status='completed', completion_date__gte=start_date)
        .annotate(month=TruncMonth('completion_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )


def get_weekly_trend(base_qs, start_date, end_date):
    """
    Single query for daily completed tasks over a date range (typically 7 days).

    Returns a queryset of dicts with 'day' (date) and 'count' (int) keys,
    ordered by day ascending.
    """
    return (
        base_qs
        .filter(
            status='completed',
            completion_date__gte=start_date,
            completion_date__lte=end_date,
        )
        .annotate(day=TruncDate('completion_date'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )


def get_dashboard_stats(base_qs, today):
    """
    Single aggregate query for all dashboard counts.

    Returns a dict with keys: 'active', 'completed', 'overdue', 'upcoming'.
    """
    active_statuses = [
        'not_started', 'processing', 'to_advisers',
        'accounting', 'oca', 'osas', 'ppss', 'supply',
    ]
    return base_qs.aggregate(
        active=Count('id', filter=Q(status__in=active_statuses)),
        completed=Count('id', filter=Q(status='completed')),
        overdue=Count('id', filter=Q(
            due_date__lt=today,
            status__in=active_statuses,
        )),
        upcoming=Count('id', filter=Q(
            due_date__gte=today,
            due_date__lte=today + timezone.timedelta(days=7),
            status__in=active_statuses,
        )),
    )


def get_report_counts(tasks_qs, today):
    """
    Single aggregate for report summary stats.

    Returns a dict with keys: 'total', 'completed', 'active', 'overdue', 'in_progress'.
    """
    return tasks_qs.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        active=Count('id', filter=~Q(status='completed')),
        overdue=Count('id', filter=Q(
            due_date__lt=today,
        ) & ~Q(status='completed')),
        in_progress=Count('id', filter=~Q(
            status__in=['not_started', 'completed'],
        )),
    )
