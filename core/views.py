from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from django.utils import timezone
from django.core.paginator import EmptyPage, PageNotAnInteger
from tasks.models import Task
from officers.models import Officer
from core.mixins import FragmentResponseMixin
from core.models import ActivityLog
from core.query_utils import get_dashboard_stats
from core.cache_utils import get_dashboard_cache_key, safe_cache_get


class DashboardView(FragmentResponseMixin, LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()

        org = user.get_organization(self.request)

        if org:
            base_qs = Task.objects.filter(organization=org, is_archived=False)
        else:
            base_qs = Task.objects.filter(is_archived=False)

        scope = self.request.GET.get('scope', 'all' if user.has_task_override else 'my_tasks')
        if scope == 'my_tasks':
            from django.db.models import Q
            base_qs = base_qs.filter(Q(assigned_officers=user) | Q(created_by=user)).distinct()
        
        ctx['scope'] = scope

        # Cache dashboard counts per user and scope with 30-second TTL
        org_id = org.pk if org else 0
        cache_key = get_dashboard_cache_key(user.pk, scope, org_id)

        def _fetch_dashboard_counts():
            return get_dashboard_stats(base_qs, today)

        counts = safe_cache_get(cache_key, _fetch_dashboard_counts, timeout=30)

        ctx['page_title'] = 'Dashboard'
        ctx['active_tasks'] = counts['active']
        ctx['completed_tasks'] = counts['completed']
        ctx['overdue_tasks'] = counts['overdue']
        ctx['upcoming_tasks'] = counts['upcoming']
        ctx['recent_tasks'] = base_qs.select_related('created_by', 'organization').prefetch_related('assigned_officers', 'assigned_officers__officer_profile', 'assigned_officers__officer_profile__position')[:10]
        
        if org:
            ctx['total_officers'] = Officer.objects.filter(user__organization=org).exclude(user__role='super_super_admin').count()
        else:
            ctx['total_officers'] = Officer.objects.exclude(user__role='super_super_admin').count()
        return ctx


from django.contrib import messages
from django.shortcuts import redirect
from organizations.models import Organization


class SettingsView(FragmentResponseMixin, LoginRequiredMixin, TemplateView):
    template_name = 'core/settings.html'

    def get_target_organization(self):
        user = self.request.user
        return user.get_organization(self.request)

    def post(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_super_admin or user.is_president or user.is_org_admin):
            messages.error(request, "Permission denied. Only organization admins and super admins can modify settings.")
            return redirect('core:settings')

        target_org = self.get_target_organization()
        if not target_org:
            messages.error(request, "No valid organization found to update settings.")
            return redirect('core:settings')

        updated_anything = False

        # Handle Organization Profile Details (Name, Abbreviation, Description)
        if 'update_details' in request.POST or request.POST.get('action') == 'update_details':
            new_name = request.POST.get('org_name', '').strip()
            new_abbr = request.POST.get('org_abbreviation', '').strip()
            new_desc = request.POST.get('org_description', '').strip()

            if new_name and new_name != target_org.name:
                if Organization.objects.filter(name__iexact=new_name).exclude(pk=target_org.pk).exists():
                    messages.error(request, f"An organization named '{new_name}' already exists.")
                else:
                    target_org.name = new_name
                    updated_anything = True

            if new_abbr != target_org.abbreviation:
                target_org.abbreviation = new_abbr
                updated_anything = True

            if new_desc != target_org.description:
                target_org.description = new_desc
                updated_anything = True

            if updated_anything:
                target_org.save()
                messages.success(request, f"Organization details updated successfully for {target_org.name}!")

        # Handle Organization Logo removal
        if request.POST.get('action') == 'remove_logo' or 'remove_logo' in request.POST:
            if target_org.logo:
                target_org.logo.delete(save=False)
                target_org.logo = None
                target_org.save()
                messages.success(request, f"Organization logo removed for {target_org.name}.")
                updated_anything = True

        # Handle Organization Logo upload/change
        if 'logo' in request.FILES:
            target_org.logo = request.FILES['logo']
            target_org.save()
            messages.success(request, f"Organization logo uploaded successfully for {target_org.name}!")
            updated_anything = True

        # Handle Organization Theme selection
        selected_theme = request.POST.get('theme')
        if selected_theme:
            valid_themes = [t[0] for t in Organization.THEME_CHOICES]
            if selected_theme in valid_themes:
                if target_org.theme != selected_theme:
                    target_org.theme = selected_theme
                    target_org.save()
                    messages.success(request, f"Theme successfully updated to '{dict(Organization.THEME_CHOICES).get(selected_theme)}' for {target_org.name}!")
            else:
                messages.error(request, "Invalid theme selection.")

        return redirect('core:settings')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'System Settings'
        target_org = self.get_target_organization()
        ctx['target_org'] = target_org
        ctx['theme_choices'] = Organization.THEME_CHOICES
        ctx['can_edit_settings'] = self.request.user.is_super_admin or self.request.user.is_president or self.request.user.is_org_admin
        return ctx


class ActivityLogView(FragmentResponseMixin, LoginRequiredMixin, ListView):
    """Activity log view with pagination at 50 items per page, ordered by timestamp descending."""
    model = ActivityLog
    template_name = 'core/activity_log.html'
    context_object_name = 'activity_logs'
    paginate_by = 50

    def get_queryset(self):
        org = self.request.user.get_organization(self.request)
        qs = ActivityLog.objects.select_related('user', 'organization')
        if org and not self.request.user.is_super_admin:
            qs = qs.filter(organization=org)

        # Apply filters
        action = self.request.GET.get('action', '')
        if action:
            qs = qs.filter(action=action)

        user_id = self.request.GET.get('user', '')
        if user_id:
            qs = qs.filter(user_id=user_id)

        # Ordered by timestamp descending (matches model Meta ordering)
        return qs.order_by('-timestamp')

    def paginate_queryset(self, queryset, page_size):
        """Override to return last available page if requested page exceeds total."""
        paginator = self.get_paginator(
            queryset, page_size, orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty()
        )
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        try:
            page_number = paginator.validate_number(page)
        except PageNotAnInteger:
            page_number = 1
        except EmptyPage:
            # Return last available page if requested page exceeds total
            page_number = paginator.num_pages
        page = paginator.page(page_number)
        return (paginator, page, page.object_list, page.has_other_pages())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Activity Log'
        ctx['current_filters'] = {
            'action': self.request.GET.get('action', ''),
            'user': self.request.GET.get('user', ''),
        }
        return ctx
