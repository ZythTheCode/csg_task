from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Count, Q, DateField
from django.db.models.functions import TruncMonth, Coalesce, Cast
from tasks.models import Task, TaskAssignment
from notifications.models import Notification
from accounts.models import User
from core.query_utils import get_dashboard_stats
import datetime
import logging

logger = logging.getLogger(__name__)


class DashboardStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    ACTIVE_STATUSES = [
        'not_started', 'processing', 'to_advisers', 'accounting',
        'oca', 'osas', 'ppss', 'supply',
    ]

    def get(self, request):
        user = request.user
        today = timezone.now().date()

        if user.can_manage_tasks:
            base_qs = Task.objects.filter(is_archived=False)
        else:
            base_qs = Task.objects.filter(assigned_officers=user, is_archived=False)
        if user.organization:
            base_qs = base_qs.filter(organization=user.organization)

        # Single aggregate query for all dashboard counts (replaces 4 separate count() calls)
        stats = get_dashboard_stats(base_qs, today)

        return Response({
            'active': stats['active'],
            'completed': stats['completed'],
            'overdue': stats['overdue'],
            'upcoming': stats['upcoming'],
        })


class DashboardChartsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        org = user.get_organization(request)
        org_id = org.id if org else 'none'
        scope = request.GET.get('scope', 'all' if user.has_task_override else 'my_tasks')

        # Check cache first
        cache_key = f'dashboard_charts_{user.id}_{org_id}_{scope}'
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = Response(cached_data)
            response['Cache-Control'] = 'private, max-age=30'
            return response
        else:
            logger.debug("Cache miss for key: %s", cache_key)

        if org:
            base_qs = Task.objects.filter(organization=org, is_archived=False)
        else:
            base_qs = Task.objects.filter(is_archived=False)

        if scope == 'my_tasks':
            base_qs = base_qs.filter(Q(assigned_officers=user) | Q(created_by=user)).distinct()

        today = timezone.now().date()

        # Status + Priority distributions in a single aggregate query
        from core.query_utils import get_distributions, get_monthly_completed, get_weekly_trend

        distributions = get_distributions(base_qs)

        # Build status distribution labels/data from the aggregate result
        status_labels = []
        status_data = []
        for code, label in Task.STATUS_CHOICES:
            status_labels.append(label)
            status_data.append(distributions.get(f'status_{code}', 0))

        # Build priority distribution labels/data from the aggregate result
        priority_labels = []
        priority_data = []
        for code, label in Task.PRIORITY_CHOICES:
            priority_labels.append(label)
            priority_data.append(distributions.get(f'priority_{code}', 0))

        # Monthly completed using TruncMonth (single query)
        start_date = datetime.date(2026, 8, 1)
        monthly_qs = get_monthly_completed(base_qs, start_date)

        # Build a lookup of month -> count from the aggregate result
        monthly_counts = {item['month'].date() if hasattr(item['month'], 'date') else item['month']: item['count'] for item in monthly_qs}

        # Generate all month labels from start_date to today
        monthly_labels = []
        monthly_data_list = []
        num_months = max(6, (today.year - 2026) * 12 + (today.month - 8 + 1))
        curr_year = 2026
        curr_month = 8

        for _ in range(num_months):
            month_start = datetime.date(curr_year, curr_month, 1)
            monthly_labels.append(month_start.strftime('%b %Y'))
            monthly_data_list.append(monthly_counts.get(month_start, 0))

            if curr_month == 12:
                curr_year += 1
                curr_month = 1
            else:
                curr_month += 1

        # Position abbreviation lookup
        POSITION_ABBREV = {
            'President': 'Pres',
            'Vice President': 'VP',
            'Secretary': 'Sec',
            'Treasurer': 'Treas',
            'Auditor': 'Aud',
            'P.R.O.': 'PRO',
            'Business Manager': 'BM',
            'Executive Assistant': 'EA',
            'Assistant Secretary': 'Asst. Sec',
            'Assistant Treasurer': 'Asst. Treas',
            'Events Manager': 'Events',
            'Graphics and Media': 'Media',
            'P.V.': 'PV',
        }

        # Tasks per officer (top 8) - already efficient with single annotated query
        officer_data = []
        officer_labels = []
        officer_counts = base_qs.values(
            'assigned_officers__id',
            'assigned_officers__first_name',
            'assigned_officers__last_name',
            'assigned_officers__username',
            'assigned_officers__officer_profile__position__title'
        ).annotate(count=Count('id')).exclude(assigned_officers__isnull=True).order_by('-count')[:8]

        for item in officer_counts:
            fname = item['assigned_officers__first_name'] or ''
            lname = item['assigned_officers__last_name'] or ''
            full_name = f"{fname} {lname}".strip() or item['assigned_officers__username'] or 'Officer'
            pos_title = item.get('assigned_officers__officer_profile__position__title') or ''
            abbrev = POSITION_ABBREV.get(pos_title) or (''.join(w[0].upper() for w in pos_title.split() if w) if pos_title else '')
            label = f"{full_name} ({abbrev})" if abbrev else full_name
            officer_labels.append(label)
            officer_data.append(item['count'])

        # Weekly trend using TruncDate (single query for last 7 days)
        week_start = today - datetime.timedelta(days=6)
        weekly_qs = get_weekly_trend(base_qs, week_start, today)

        # Build a lookup of day -> count from the aggregate result
        weekly_counts = {item['day']: item['count'] for item in weekly_qs}

        # Generate all day labels for the last 7 days
        weekly_labels = []
        weekly_data = []
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            weekly_labels.append(day.strftime('%a %d'))
            weekly_data.append(weekly_counts.get(day, 0))

        response = Response({
            'status_distribution': {'labels': status_labels, 'data': status_data},
            'priority_distribution': {'labels': priority_labels, 'data': priority_data},
            'monthly_completed': {'labels': monthly_labels, 'data': monthly_data_list},
            'tasks_per_officer': {'labels': officer_labels, 'data': officer_data},
            'weekly_trend': {'labels': weekly_labels, 'data': weekly_data},
        })
        response['Cache-Control'] = 'max-age=15'
        return response


class TaskListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.can_manage_tasks:
            tasks = Task.objects.filter(is_archived=False)
        else:
            tasks = Task.objects.filter(assigned_officers=user, is_archived=False)
        if user.organization:
            tasks = tasks.filter(organization=user.organization)

        tasks = tasks.select_related('organization').only(
            'id', 'task_number', 'title', 'status', 'priority', 'progress', 'due_date',
            'organization__id', 'organization__name',
        )

        data = []
        for t in tasks[:50]:
            data.append({
                'id': t.id,
                'task_number': t.task_number,
                'title': t.title,
                'status': t.status,
                'priority': t.priority,
                'progress': t.progress,
                'due_date': str(t.due_date) if t.due_date else None,
            })
        return Response(data)


class TaskDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        return Response({
            'id': task.id,
            'task_number': task.task_number,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'progress': task.progress,
            'due_date': str(task.due_date) if task.due_date else None,
            'completion_date': str(task.completion_date) if task.completion_date else None,
        })


class UnreadNotificationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifs = (
            Notification.objects.filter(recipient=request.user, is_read=False)
            .select_related('related_task')
            .only('id', 'title', 'message', 'notification_type', 'created_at', 'related_task_id')
        )[:10]
        data = [{'id': n.id, 'title': n.title, 'message': n.message, 'type': n.notification_type, 'created_at': str(n.created_at), 'related_task_id': n.related_task_id} for n in notifs]
        return Response({'count': len(data), 'notifications': data})


class MarkNotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, recipient=request.user)
            notif.is_read = True
            notif.save()
            return Response({'status': 'ok'})
        except Notification.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
