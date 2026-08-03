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

        org = self.request.user.organization
        officers_qs = Officer.objects.select_related('user', 'position')
        if org:
            officers_qs = officers_qs.filter(user__organization=org)
            tasks_base_qs = Task.objects.filter(organization=org)
        else:
            tasks_base_qs = Task.objects.all()

        # Officer productivity
        officers_data = []
        for officer in officers_qs:
            user = officer.user
            total = tasks_base_qs.filter(assigned_officers=user).count()
            completed = tasks_base_qs.filter(assigned_officers=user, status='completed').count()
            active = tasks_base_qs.filter(assigned_officers=user).exclude(status='completed').count()
            overdue = tasks_base_qs.filter(assigned_officers=user, due_date__lt=today).exclude(status='completed').count()
            rate = round(completed / total * 100) if total > 0 else 0
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
        ctx['upcoming_deadlines'] = tasks_base_qs.filter(
            due_date__gte=today,
            due_date__lte=today + datetime.timedelta(days=7),
            is_archived=False
        ).exclude(status='completed').prefetch_related('assigned_officers').order_by('due_date')

        # Delayed tasks
        ctx['delayed_tasks'] = tasks_base_qs.filter(
            due_date__lt=today,
            is_archived=False
        ).exclude(status='completed').prefetch_related('assigned_officers').order_by('due_date')

        # Overall stats
        total_tasks = tasks_base_qs.filter(is_archived=False).count()
        completed_tasks = tasks_base_qs.filter(status='completed', is_archived=False).count()
        ctx['overall_completion_rate'] = round(completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        ctx['total_tasks'] = total_tasks
        ctx['completed_tasks'] = completed_tasks

        return ctx
