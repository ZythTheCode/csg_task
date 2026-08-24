from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q
from core.mixins import FragmentResponseMixin
from core.query_utils import get_report_counts
from tasks.models import Task
from officers.models import Officer
from accounts.models import User
import io
import datetime


class ReportsDashboardView(FragmentResponseMixin, LoginRequiredMixin, TemplateView):
    template_name = 'reports/dashboard.html'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not getattr(request.user, 'can_view_reports', False):
            from django.shortcuts import redirect
            from django.contrib import messages
            messages.error(request, 'You do not have permission to view reports.')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Reports'
        ctx['status_choices'] = Task.STATUS_CHOICES
        ctx['priority_choices'] = Task.PRIORITY_CHOICES
        org = self.request.user.get_organization(self.request)
        
        # Cache officers list for filter dropdown (TTL 300s)
        org_id = org.pk if org else 'all'
        cache_key = f'reports_officers_{org_id}'
        officers = cache.get(cache_key)
        if officers is None:
            officers_qs = Officer.objects.select_related('user').exclude(user__role__in=['super_admin', 'super_super_admin'])
            if org:
                officers_qs = officers_qs.filter(user__organization=org)
            officers = list(officers_qs.all())
            cache.set(cache_key, officers, 300)
        ctx['officers'] = officers

        # Apply filters
        filters = self._get_filters()
        tasks = self._get_filtered_tasks(filters)
        ctx['filters'] = filters
        ctx['scope'] = filters['scope']

        # Use single aggregate query for all counts instead of multiple count() calls
        today = timezone.now().date()
        report_counts = get_report_counts(tasks, today)
        ctx['task_count'] = report_counts['total']
        ctx['active_count'] = report_counts['active']
        ctx['completed_count'] = report_counts['completed']

        # Summary stats from the single aggregate (no additional queries)
        ctx['summary'] = {
            'total': report_counts['total'],
            'completed': report_counts['completed'],
            'overdue': report_counts['overdue'],
            'in_progress': report_counts['in_progress'],
        }

        # Paginate active tasks at 25 items per page
        active_tasks_qs = tasks.exclude(status='completed')
        active_paginator = Paginator(active_tasks_qs, self.paginate_by)
        active_page_number = self.request.GET.get('active_page', 1)
        try:
            active_page = active_paginator.page(active_page_number)
        except PageNotAnInteger:
            active_page = active_paginator.page(1)
        except EmptyPage:
            active_page = active_paginator.page(active_paginator.num_pages)

        ctx['active_tasks'] = active_page
        ctx['active_page_obj'] = active_page

        # Paginate completed tasks at 25 items per page
        completed_tasks_qs = tasks.filter(status='completed')
        completed_paginator = Paginator(completed_tasks_qs, self.paginate_by)
        completed_page_number = self.request.GET.get('completed_page', 1)
        try:
            completed_page = completed_paginator.page(completed_page_number)
        except PageNotAnInteger:
            completed_page = completed_paginator.page(1)
        except EmptyPage:
            completed_page = completed_paginator.page(completed_paginator.num_pages)

        ctx['completed_tasks'] = completed_page
        ctx['completed_page_obj'] = completed_page

        # Keep full queryset reference for exports (not evaluated here)
        ctx['tasks'] = tasks
        return ctx

    def _get_filters(self):
        req = self.request
        return {
            'officer': req.GET.get('officer', ''),
            'month': req.GET.get('month', ''),
            'year': req.GET.get('year', ''),
            'status': req.GET.get('status', ''),
            'priority': req.GET.get('priority', ''),
            'scope': req.GET.get('scope', 'all' if req.user.has_task_override else 'my_tasks'),
        }

    def _get_filtered_tasks(self, filters):
        qs = Task.objects.filter(is_archived=False).select_related('created_by', 'organization').prefetch_related('assigned_officers', 'assigned_officers__officer_profile', 'assigned_officers__officer_profile__position')
        org = self.request.user.get_organization(self.request)
        if org:
            qs = qs.filter(organization=org)
            
        if filters['scope'] == 'my_tasks':
            qs = qs.filter(Q(assigned_officers=self.request.user) | Q(created_by=self.request.user)).distinct()

        if filters['officer']:
            qs = qs.filter(assigned_officers__id=filters['officer'])
        if filters['year']:
            try:
                y = int(filters['year'])
                qs = qs.filter(Q(due_date__year=y) | Q(created_at__year=y))
            except ValueError:
                pass
        if filters['month']:
            try:
                m = int(filters['month'])
                qs = qs.filter(Q(due_date__month=m) | Q(created_at__month=m))
            except ValueError:
                pass
        if filters['status']:
            if filters['status'] == 'in_progress':
                qs = qs.exclude(status__in=['not_started', 'completed'])
            else:
                qs = qs.filter(status=filters['status'])
        if filters['priority']:
            qs = qs.filter(priority=filters['priority'])
        return qs


from core.query_utils import get_export_queryset, get_report_counts
from core.export_utils import generate_tasks_pdf, generate_tasks_excel
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.utils.decorators import method_decorator

@method_decorator(xframe_options_sameorigin, name='dispatch')
class ExportReportPDFView(LoginRequiredMixin, View):
    def get(self, request):
        tasks = get_export_queryset(request)
        response = generate_tasks_pdf(tasks, filename="csg_report.pdf")
        if request.GET.get('download') == '1':
            response['Content-Disposition'] = 'attachment; filename="csg_report.pdf"'
        return response


class ExportReportExcelView(LoginRequiredMixin, View):
    def get(self, request):
        tasks = get_export_queryset(request)
        return generate_tasks_excel(tasks, filename="csg_report.xlsx")
