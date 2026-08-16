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

        counts = base_qs.aggregate(
            active=Count('id', filter=Q(status__in=self.ACTIVE_STATUSES)),
            completed=Count('id', filter=Q(status='completed')),
            overdue=Count('id', filter=Q(
                due_date__lt=today,
                status__in=self.ACTIVE_STATUSES,
            )),
            upcoming=Count('id', filter=Q(
                due_date__gte=today,
                due_date__lte=today + datetime.timedelta(days=7),
                status__in=self.ACTIVE_STATUSES,
            )),
        )

        response = Response(counts)
        response['Cache-Control'] = 'private, max-age=30'
        return response


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

        # Status and priority distribution (single aggregate query)
        agg = base_qs.aggregate(
            **{f'status_{s}': Count('id', filter=Q(status=s)) for s, _ in Task.STATUS_CHOICES},
            **{f'priority_{p}': Count('id', filter=Q(priority=p)) for p, _ in Task.PRIORITY_CHOICES},
        )

        status_data = {label: agg[f'status_{s}'] for s, label in Task.STATUS_CHOICES}
        priority_data = {label: agg[f'priority_{p}'] for p, label in Task.PRIORITY_CHOICES}

        # Monthly completed (starting in August 2026) — single TruncMonth query
        start_year = 2026
        start_month = 8  # August 2026
        start_date = datetime.date(start_year, start_month, 1)

        # Annotate effective completion date: completion_date if set, else updated_at cast to date
        monthly_qs = (
            base_qs
            .filter(status='completed')
            .annotate(
                effective_date=Coalesce(
                    'completion_date',
                    Cast('updated_at', output_field=DateField()),
                    output_field=DateField()
                )
            )
            .filter(effective_date__gte=start_date)
            .annotate(month=TruncMonth('effective_date'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        # Build a lookup from month to count
        month_counts = {entry['month']: entry['count'] for entry in monthly_qs}

        # Generate all months from start to current, filling in 0 for months with no completions
        num_months = max(6, (today.year - start_year) * 12 + (today.month - start_month + 1))
        monthly_labels = []
        monthly_data = []
        curr_year = start_year
        curr_month = start_month
        for _ in range(num_months):
            month_key = datetime.date(curr_year, curr_month, 1)
            monthly_labels.append(month_key.strftime('%b %Y'))
            monthly_data.append(month_counts.get(month_key, 0))
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

        # Tasks per officer (top 8)
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

        # Weekly trend (last 7 days) — single query with conditional aggregation
        weekly_agg = base_qs.filter(status='completed').aggregate(
            **{
                f'day_{i}': Count('id', filter=Q(
                    Q(completion_date=today - datetime.timedelta(days=6 - i)) |
                    Q(completion_date__isnull=True, updated_at__date=today - datetime.timedelta(days=6 - i))
                ))
                for i in range(7)
            }
        )
        weekly_labels = [(today - datetime.timedelta(days=6 - i)).strftime('%a %d') for i in range(7)]
        weekly_data = [weekly_agg[f'day_{i}'] for i in range(7)]

        response_data = {
            'status_distribution': {'labels': list(status_data.keys()), 'data': list(status_data.values())},
            'priority_distribution': {'labels': list(priority_data.keys()), 'data': list(priority_data.values())},
            'monthly_completed': {'labels': monthly_labels, 'data': monthly_data},
            'tasks_per_officer': {'labels': officer_labels, 'data': officer_data},
            'weekly_trend': {'labels': weekly_labels, 'data': weekly_data},
        }

        # Cache the response data
        cache.set(cache_key, response_data, 30)

        response = Response(response_data)
        response['Cache-Control'] = 'private, max-age=30'
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

        data = list(tasks.select_related('created_by', 'organization').values(
            'id', 'task_number', 'title', 'status',
            'priority', 'progress', 'due_date'
        )[:50])
        response = Response(data)
        response['Cache-Control'] = 'private, max-age=0'
        return response


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
        notifs = list(
            Notification.objects.filter(recipient=request.user, is_read=False)
            .select_related('related_task')
            .only('id', 'title', 'message', 'notification_type', 'created_at')
            .order_by('-created_at')[:10]
        )
        data = [{'id': n.id, 'title': n.title, 'message': n.message, 'type': n.notification_type, 'created_at': str(n.created_at)} for n in notifs]
        response = Response({'count': len(notifs), 'notifications': data})
        response['Cache-Control'] = 'private, max-age=0'
        return response


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
