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


def get_export_queryset(request):
    """
    Consolidated filtering logic for all exports (PDF/Excel) from both Tasks and Reports modules.
    """
    from tasks.models import Task
    
    qs = Task.objects.filter(is_archived=False)
    
    if hasattr(request.user, 'get_organization'):
        org = request.user.get_organization(request)
        if org:
            qs = qs.filter(organization=org)
    elif request.user.organization:
        qs = qs.filter(organization=request.user.organization)

    task_ids = request.GET.get('task_ids', '')
    if task_ids:
        qs = qs.filter(id__in=task_ids.split(','))
        return qs.select_related('created_by').prefetch_related('assigned_officers', 'assigned_officers__officer_profile', 'assigned_officers__officer_profile__position')

    scope = request.GET.get('scope', 'all' if request.user.has_task_override else 'my_tasks')
    if scope == 'my_tasks':
        qs = qs.filter(Q(assigned_officers=request.user) | Q(created_by=request.user)).distinct()

    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(task_number__icontains=q) | Q(description__icontains=q))

    status = request.GET.get('status', '')
    if status:
        if status == 'active':
            qs = qs.exclude(status='completed')
        elif status == 'overdue':
            qs = qs.filter(due_date__lt=timezone.now().date()).exclude(status='completed')
        elif status == 'in_progress':
            qs = qs.exclude(status__in=['not_started', 'completed'])
        else:
            qs = qs.filter(status=status)

    priority = request.GET.get('priority', '')
    if priority:
        qs = qs.filter(priority=priority)

    # Handle multiple officers (from tasks list) or single officer (from reports)
    officers = request.GET.getlist('officer')
    if not officers and request.GET.get('officer'):
        officers = [request.GET.get('officer')]
    # filter out empty string from officers list
    officers = [o for o in officers if o]
    if officers:
        qs = qs.filter(assigned_officers__id__in=officers).distinct()

    year = request.GET.get('year', '')
    if year:
        try:
            y = int(year)
            qs = qs.filter(Q(due_date__year=y) | Q(created_at__year=y))
        except ValueError:
            pass

    month = request.GET.get('month', '')
    if month:
        try:
            m = int(month)
            qs = qs.filter(Q(due_date__month=m) | Q(created_at__month=m))
        except ValueError:
            pass

    return qs.select_related('created_by').prefetch_related('assigned_officers', 'assigned_officers__officer_profile', 'assigned_officers__officer_profile__position')
