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

        org = self.request.user.get_organization(self.request)
        officers_qs = Officer.objects.select_related('user', 'position').exclude(user__role='super_super_admin')
        if org:
            officers_qs = officers_qs.filter(user__organization=org)
            tasks_base_qs = Task.objects.filter(organization=org)
        else:
            tasks_base_qs = Task.objects.all()

        officers_qs = officers_qs.annotate(
            total_count=Count('user__assigned_tasks', filter=Q(user__assigned_tasks__is_archived=False)),
            completed_count=Count('user__assigned_tasks', filter=Q(user__assigned_tasks__status='completed', user__assigned_tasks__is_archived=False)),
            active_count=Count('user__assigned_tasks', filter=Q(user__assigned_tasks__is_archived=False) & ~Q(user__assigned_tasks__status='completed')),
            overdue_count=Count('user__assigned_tasks', filter=Q(user__assigned_tasks__due_date__lt=today, user__assigned_tasks__is_archived=False) & ~Q(user__assigned_tasks__status='completed'))
        )

        officers_data = []
        for officer in officers_qs:
            total = officer.total_count
            completed = officer.completed_count
            active = officer.active_count
            overdue = officer.overdue_count
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
        ).exclude(status='completed').select_related('created_by', 'organization').prefetch_related('assigned_officers', 'assigned_officers__officer_profile', 'assigned_officers__officer_profile__position').order_by('due_date')

        # Delayed tasks
        ctx['delayed_tasks'] = tasks_base_qs.filter(
            due_date__lt=today,
            is_archived=False
        ).exclude(status='completed').select_related('created_by', 'organization').prefetch_related('assigned_officers', 'assigned_officers__officer_profile', 'assigned_officers__officer_profile__position').order_by('due_date')

        # Overall stats
        total_tasks = tasks_base_qs.filter(is_archived=False).count()
        completed_tasks = tasks_base_qs.filter(status='completed', is_archived=False).count()
        ctx['overall_completion_rate'] = round(completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        ctx['total_tasks'] = total_tasks
        ctx['completed_tasks'] = completed_tasks

        return ctx
