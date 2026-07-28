from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils import timezone
from tasks.models import Task
from officers.models import Officer


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()

        active_statuses = ['not_started', 'processing', 'to_advisers', 'accounting', 'oca', 'osas', 'ppss', 'supply']

        # Update overdue statuses
        Task.objects.filter(
            due_date__lt=today,
            status__in=active_statuses
        ).update(status='overdue')

        if user.can_manage_tasks:
            base_qs = Task.objects.filter(is_archived=False)
        else:
            base_qs = Task.objects.filter(assigned_officers=user, is_archived=False)

        ctx['page_title'] = 'Dashboard'
        ctx['active_tasks'] = base_qs.filter(status__in=active_statuses).count()
        ctx['completed_tasks'] = base_qs.filter(status='completed').count()
        ctx['overdue_tasks'] = base_qs.filter(status='overdue').count()
        ctx['upcoming_tasks'] = base_qs.filter(
            due_date__gte=today,
            due_date__lte=today + timezone.timedelta(days=7),
            status__in=active_statuses
        ).count()
        ctx['recent_tasks'] = base_qs.select_related('created_by').prefetch_related('assigned_officers')[:10]
        ctx['total_officers'] = Officer.objects.count()
        return ctx


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/settings.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'System Settings'
        return ctx
