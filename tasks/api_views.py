from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Q
from tasks.models import Task, TaskAssignment
from notifications.models import Notification
from accounts.models import User
import datetime


class DashboardStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()

        if user.can_manage_tasks:
            base_qs = Task.objects.filter(is_archived=False)
        else:
            base_qs = Task.objects.filter(assigned_officers=user, is_archived=False)

        return Response({
            'active': base_qs.filter(status__in=['pending', 'not_started', 'in_progress', 'waiting_approval']).count(),
            'completed': base_qs.filter(status='completed').count(),
            'overdue': base_qs.filter(status='overdue').count(),
            'upcoming': base_qs.filter(
                due_date__gte=today,
                due_date__lte=today + datetime.timedelta(days=7),
                status__in=['pending', 'not_started', 'in_progress']
            ).count(),
        })


class DashboardChartsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.can_manage_tasks:
            base_qs = Task.objects.filter(is_archived=False)
        else:
            base_qs = Task.objects.filter(assigned_officers=user, is_archived=False)

        today = timezone.now().date()

        # Status distribution
        status_data = {}
        for s, label in Task.STATUS_CHOICES:
            status_data[label] = base_qs.filter(status=s).count()

        # Priority distribution
        priority_data = {}
        for p, label in Task.PRIORITY_CHOICES:
            priority_data[label] = base_qs.filter(priority=p).count()

        # Monthly completed (last 6 months)
        monthly_labels = []
        monthly_data = []
        for i in range(5, -1, -1):
            d = today.replace(day=1) - datetime.timedelta(days=i * 28)
            month_start = d.replace(day=1)
            if d.month == 12:
                month_end = d.replace(year=d.year + 1, month=1, day=1) - datetime.timedelta(days=1)
            else:
                month_end = d.replace(month=d.month + 1, day=1) - datetime.timedelta(days=1)
            count = base_qs.filter(status='completed', completion_date__gte=month_start, completion_date__lte=month_end).count()
            monthly_labels.append(month_start.strftime('%b %Y'))
            monthly_data.append(count)

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
        assignments = TaskAssignment.objects.filter(
            task__is_archived=False
        ).select_related('officer__officer_profile__position') \
         .values('officer__first_name', 'officer__last_name',
                 'officer__officer_profile__position__title') \
         .annotate(count=Count('id')).order_by('-count')[:8]
        for a in assignments:
            full_name = f"{a['officer__first_name']} {a['officer__last_name']}".strip() or 'Unknown'
            pos_title = a.get('officer__officer_profile__position__title') or ''
            abbrev = POSITION_ABBREV.get(pos_title) or ''.join(w[0].upper() for w in pos_title.split() if w)
            label = f"{full_name} ({abbrev})" if abbrev else full_name
            officer_labels.append(label)
            officer_data.append(a['count'])

        # Weekly trend (last 7 days)
        weekly_labels = []
        weekly_data = []
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            count = base_qs.filter(completion_date=day).count()
            weekly_labels.append(day.strftime('%a %d'))
            weekly_data.append(count)

        return Response({
            'status_distribution': {'labels': list(status_data.keys()), 'data': list(status_data.values())},
            'priority_distribution': {'labels': list(priority_data.keys()), 'data': list(priority_data.values())},
            'monthly_completed': {'labels': monthly_labels, 'data': monthly_data},
            'tasks_per_officer': {'labels': officer_labels, 'data': officer_data},
            'weekly_trend': {'labels': weekly_labels, 'data': weekly_data},
        })


class TaskListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.can_manage_tasks:
            tasks = Task.objects.filter(is_archived=False)
        else:
            tasks = Task.objects.filter(assigned_officers=user, is_archived=False)

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
        notifs = Notification.objects.filter(recipient=request.user, is_read=False)[:10]
        data = [{'id': n.id, 'title': n.title, 'message': n.message, 'type': n.notification_type, 'created_at': str(n.created_at)} for n in notifs]
        return Response({'count': notifs.count(), 'notifications': data})


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
