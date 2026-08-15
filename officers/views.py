from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from .models import Position, Officer
from .forms import PositionForm, OfficerForm
from accounts.models import User


class OfficerListView(LoginRequiredMixin, ListView):
    model = Officer
    template_name = 'officers/list.html'
    context_object_name = 'officers'

    def get_queryset(self):
        from django.db.models import Count, Q
        org = self.request.user.get_organization(self.request)
        qs = Officer.objects.select_related('user', 'position').exclude(
            user__role__in=['super_admin', 'super_super_admin']
        ).annotate(
            annotated_total=Count('user__task_assignments'),
            annotated_completed=Count('user__task_assignments', filter=Q(user__task_assignments__task__status='completed')),
            annotated_active=Count('user__task_assignments', filter=Q(user__task_assignments__task__is_archived=False) & ~Q(user__task_assignments__task__status='completed'))
        ).order_by('user__last_name', 'user__first_name')
        if org:
            qs = qs.filter(user__organization=org)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Officers'
        return ctx


class OfficerDetailView(LoginRequiredMixin, DetailView):
    model = Officer
    template_name = 'officers/detail.html'
    context_object_name = 'officer'

    def get_queryset(self):
        org = self.request.user.get_organization(self.request)
        qs = Officer.objects.select_related('user', 'position').exclude(user__role__in=['super_admin', 'super_super_admin'])
        if org and not self.request.user.is_super_admin:
            qs = qs.filter(user__organization=org)
        return qs

    def dispatch(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Exception:
            messages.warning(request, 'This officer profile has already been deleted or no longer exists.')
            return redirect('officers:list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from tasks.models import Task
        from django.db.models import Count, Q
        officer_user = self.object.user
        ctx['page_title'] = f'Officer: {officer_user.get_full_name()}'
        ctx['assigned_tasks'] = Task.objects.filter(assigned_officers=officer_user, is_archived=False).select_related('created_by', 'organization').prefetch_related('assigned_officers', 'assigned_officers__officer_profile', 'assigned_officers__officer_profile__position')[:10]
        # Use a single aggregated query for task counts
        from tasks.models import TaskAssignment
        counts = TaskAssignment.objects.filter(officer=officer_user).aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(task__status='completed')),
            active=Count('id', filter=~Q(task__status='completed') & Q(task__is_archived=False)),
        )
        ctx['total_tasks'] = counts['total']
        ctx['completed_tasks'] = counts['completed']
        ctx['active_tasks'] = counts['active']
        return ctx


class OfficerCreateView(LoginRequiredMixin, CreateView):
    model = Officer
    form_class = OfficerForm
    template_name = 'officers/form.html'
    success_url = reverse_lazy('officers:list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_officers:
            messages.error(request, 'Permission denied.')
            return redirect('officers:list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Add Officer'
        ctx['form_action'] = 'Create Officer'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object.user
        created_pass = form.cleaned_data.get('password') or 'admin123'
        messages.success(
            self.request,
            f"Officer '{user.get_full_name()}' created successfully! Assigned Username: '{user.username}' (Password: '{created_pass}')."
        )
        return response


class OfficerUpdateView(LoginRequiredMixin, UpdateView):
    model = Officer
    form_class = OfficerForm
    template_name = 'officers/form.html'

    def get_queryset(self):
        qs = Officer.objects.select_related('user', 'position')
        org = self.request.user.get_organization(self.request)
        if org:
            qs = qs.filter(user__organization=org)
        return qs

    def get_success_url(self):
        return reverse_lazy('officers:list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_officers:
            messages.error(request, 'Permission denied.')
            return redirect('officers:list')
        try:
            self.object = self.get_object()
        except Exception:
            messages.warning(request, 'This officer account has already been deleted or no longer exists.')
            return redirect('officers:list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['request'] = self.request
        return kwargs

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object:
            messages.warning(request, 'This officer account has already been deleted or no longer exists.')
            return redirect('officers:list')
        if request.POST.get('action') == 'remove_photo':
            if self.object.user and self.object.user.profile_picture:
                user_name = self.object.user.get_full_name()
                self.object.user.profile_picture.delete(save=False)
                self.object.user.profile_picture = None
                self.object.user.save(update_fields=['profile_picture'])
                from core.services.audit import log_activity
                log_activity(request, 'OFFICER_PHOTO_REMOVE', f"Removed profile photo for officer '{user_name}'.", resource_type='Officer', resource_id=self.object.pk)
                messages.success(request, f"Profile picture for '{user_name}' removed successfully.")
            return redirect('officers:list')
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Edit Officer: {self.object.user.get_full_name()}'
        ctx['form_action'] = 'Save Changes'
        return ctx


class OfficerDeleteView(LoginRequiredMixin, DeleteView):
    model = Officer
    success_url = reverse_lazy('officers:list')

    def get_queryset(self):
        qs = Officer.objects.select_related('user', 'position')
        if not self.request.user.is_super_admin:
            org = self.request.user.get_organization(self.request)
            if org:
                qs = qs.filter(user__organization=org)
        return qs

    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_officers:
            messages.error(request, 'Access denied. Only Super Admin can delete user accounts.')
            return redirect('officers:list')
        try:
            self.object = self.get_object()
        except Exception:
            messages.warning(request, "This officer account has already been deleted or no longer exists.")
            return redirect('officers:list')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except Exception:
            return None

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object:
            messages.warning(request, "This officer account has already been deleted or no longer exists.")
            return redirect(self.success_url)

        confirm_text = request.POST.get('confirm_text', '').strip()
        if confirm_text.upper() != 'DELETE':
            messages.error(request, "Deletion failed. You must type 'DELETE' to confirm account deletion.")
            return redirect('officers:list')

        user = self.object.user
        user_name = user.get_full_name() or user.username if user else 'Officer'
        user_pk = user.pk if user else None

        from django.db import transaction
        with transaction.atomic():
            if user:
                from notifications.models import Notification
                from tasks.models import TaskAssignment
                Notification.objects.filter(recipient=user).delete()
                TaskAssignment.objects.filter(officer=user).delete()
                user.delete()
            else:
                self.object.delete()

        from core.services.audit import log_activity
        log_activity(request, 'OFFICER_DELETE', f"Deleted officer account '{user_name}'", resource_type='Officer', resource_id=user_pk)
        messages.success(request, f"User account '{user_name}' has been permanently deleted.")
        return redirect(self.success_url)


class PositionListView(LoginRequiredMixin, ListView):
    model = Position
    template_name = 'officers/positions.html'
    context_object_name = 'positions'

    def get_queryset(self):
        org = self.request.user.get_organization(self.request)
        qs = Position.objects.select_related('officer__user')
        if org:
            qs = qs.filter(organization=org)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Positions'
        return ctx


class PositionCreateView(LoginRequiredMixin, CreateView):
    model = Position
    form_class = PositionForm
    template_name = 'officers/position_form.html'
    success_url = reverse_lazy('officers:position_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_officers:
            messages.error(request, 'Permission denied.')
            return redirect('officers:position_list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        org = self.request.user.get_organization(self.request)
        form.instance.organization = org or self.request.user.organization
        resp = super().form_valid(form)
        from core.services.audit import log_activity
        log_activity(self.request, 'POSITION_CREATE', f"Created position '{self.object.title}' ({self.object.get_initials()})", resource_type='Position', resource_id=self.object.pk)
        return resp

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Add Position'
        ctx['form_action'] = 'Create Position'
        return ctx


class PositionUpdateView(LoginRequiredMixin, UpdateView):
    model = Position
    form_class = PositionForm
    template_name = 'officers/position_form.html'
    success_url = reverse_lazy('officers:position_list')

    def get_queryset(self):
        qs = Position.objects.all()
        org = self.request.user.get_organization(self.request)
        if org:
            qs = qs.filter(organization=org)
        return qs

    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_officers:
            messages.error(request, 'Permission denied.')
            return redirect('officers:position_list')
        try:
            self.object = self.get_object()
        except Exception:
            messages.warning(request, 'This position has already been deleted or no longer exists.')
            return redirect('officers:position_list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        resp = super().form_valid(form)
        from core.services.audit import log_activity
        log_activity(self.request, 'POSITION_UPDATE', f"Updated position '{self.object.title}' ({self.object.get_initials()})", resource_type='Position', resource_id=self.object.pk)
        return resp

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Edit Position: {self.object.title}'
        ctx['form_action'] = 'Save Changes'
        return ctx


class PositionDeleteView(LoginRequiredMixin, DeleteView):
    model = Position
    template_name = 'officers/position_confirm_delete.html'
    success_url = reverse_lazy('officers:position_list')

    def get_queryset(self):
        qs = Position.objects.all()
        org = self.request.user.get_organization(self.request)
        if org:
            qs = qs.filter(organization=org)
        return qs

    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_officers:
            messages.error(request, 'Access denied. Only Super Admin can delete positions.')
            return redirect('officers:position_list')
        try:
            self.object = self.get_object()
        except Exception:
            messages.warning(request, 'This position has already been deleted or no longer exists.')
            return redirect('officers:position_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Delete Position: {self.object.title}'
        try:
            ctx['assigned_officer'] = self.object.officer
        except Officer.DoesNotExist:
            ctx['assigned_officer'] = None
        return ctx

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Exception:
            messages.warning(request, 'This position has already been deleted or no longer exists.')
            return redirect(self.success_url)

        if not self.object:
            messages.warning(request, 'This position has already been deleted or no longer exists.')
            return redirect(self.success_url)

        position_title = self.object.title
        position_pk = self.object.pk
        self.object.delete()
        from core.services.audit import log_activity
        log_activity(request, 'POSITION_DELETE', f"Deleted position '{position_title}'", resource_type='Position', resource_id=position_pk)
        messages.success(request, f"Position '{position_title}' has been deleted. Affected officers' positions have been cleared.")
        return redirect(self.success_url)
