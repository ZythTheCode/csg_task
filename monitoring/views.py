from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Count, Q
from tasks.models import Task, TaskAssignment
from officers.models import Officer
from accounts.models import User
import datetime


class MonitoringDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'monitoring/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        ctx['page_title'] = 'Monitoring Dashboard'

        # Officer productivity
        officers_data = []
        for officer in Officer.objects.select_related('user', 'position'):
            user = officer.user
            total = Task.objects.filter(assigned_officers=user).count()
            completed = Task.objects.filter(assigned_officers=user, status='completed').count()
            active = Task.objects.filter(assigned_officers=user, status__in=['in_progress', 'pending', 'not_started']).count()
            overdue = Task.objects.filter(assigned_officers=user, status='overdue').count()
            rate = round((completed / total * 100), 1) if total > 0 else 0
            officers_data.append({
                'officer': officer,
                'total': total,
                'completed': completed,
                'active': active,
                'overdue': overdue,
                'completion_rate': rate,
            })
        officers_data.sort(key=lambda x: x['completion_rate'], reverse=True)
        ctx['officers_data'] = officers_data

        # Upcoming deadlines (next 7 days)
        ctx['upcoming_deadlines'] = Task.objects.filter(
            due_date__gte=today,
            due_date__lte=today + datetime.timedelta(days=7),
            status__in=['pending', 'not_started', 'in_progress'],
            is_archived=False
        ).prefetch_related('assigned_officers').order_by('due_date')

        # Delayed tasks
        ctx['delayed_tasks'] = Task.objects.filter(
            status='overdue',
            is_archived=False
        ).prefetch_related('assigned_officers').order_by('due_date')

        # Overall stats
        total_tasks = Task.objects.filter(is_archived=False).count()
        completed_tasks = Task.objects.filter(status='completed').count()
        ctx['overall_completion_rate'] = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
        ctx['total_tasks'] = total_tasks
        ctx['completed_tasks'] = completed_tasks

        return ctx
