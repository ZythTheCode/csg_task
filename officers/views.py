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
        qs = Officer.objects.select_related('user', 'position').order_by('user__last_name')
        if self.request.user.organization:
            qs = qs.filter(user__organization=self.request.user.organization)
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
        qs = Officer.objects.select_related('user', 'position')
        if self.request.user.organization:
            qs = qs.filter(user__organization=self.request.user.organization)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from tasks.models import Task
        officer_user = self.object.user
        ctx['page_title'] = f'Officer: {officer_user.get_full_name()}'
        ctx['assigned_tasks'] = Task.objects.filter(assigned_officers=officer_user, is_archived=False)[:10]
        ctx['total_tasks'] = Task.objects.filter(assigned_officers=officer_user).count()
        ctx['completed_tasks'] = Task.objects.filter(assigned_officers=officer_user, status='completed').count()
        ctx['active_tasks'] = Task.objects.filter(assigned_officers=officer_user).exclude(status='completed').count()
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
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Add Officer'
        ctx['form_action'] = 'Create Officer'
        return ctx


class OfficerUpdateView(LoginRequiredMixin, UpdateView):
    model = Officer
    form_class = OfficerForm
    template_name = 'officers/form.html'

    def get_queryset(self):
        qs = Officer.objects.select_related('user', 'position')
        if self.request.user.organization:
            qs = qs.filter(user__organization=self.request.user.organization)
        return qs

    def get_success_url(self):
        return reverse_lazy('officers:detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_officers:
            messages.error(request, 'Permission denied.')
            return redirect('officers:list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST.get('action') == 'remove_photo':
            if self.object.user and self.object.user.profile_picture:
                user_name = self.object.user.get_full_name()
                self.object.user.profile_picture.delete(save=False)
                self.object.user.profile_picture = None
                self.object.user.save(update_fields=['profile_picture'])
                from core.services.audit import log_activity
                log_activity(request, 'OFFICER_PHOTO_REMOVE', f"Removed profile photo for officer '{user_name}'.", resource_type='Officer', resource_id=self.object.pk)
                messages.success(request, f"Profile picture for '{user_name}' removed successfully.")
            return redirect('officers:detail', pk=self.object.pk)
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
        if self.request.user.organization:
            qs = qs.filter(user__organization=self.request.user.organization)
        return qs

    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_officers:
            messages.error(request, 'Access denied. Only Super Admin can delete user accounts.')
            return redirect('officers:list')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        confirm_text = request.POST.get('confirm_text', '').strip()
        if confirm_text.upper() != 'DELETE':
            messages.error(request, "Deletion failed. You must type 'DELETE' to confirm account deletion.")
            return redirect('officers:list')

        user = self.object.user
        user_name = user.get_full_name() or user.username if user else 'Officer'
        user_pk = user.pk if user else None
        self.object.delete()
        if user:
            user.delete()
        from core.services.audit import log_activity
        log_activity(request, 'OFFICER_DELETE', f"Deleted officer account '{user_name}'", resource_type='Officer', resource_id=user_pk)
        messages.success(request, f"User account '{user_name}' has been permanently deleted.")
        return redirect(self.success_url)


class PositionListView(LoginRequiredMixin, ListView):
    model = Position
    template_name = 'officers/positions.html'
    context_object_name = 'positions'

    def get_queryset(self):
        qs = Position.objects.select_related('officer__user')
        if self.request.user.organization:
            qs = qs.filter(organization=self.request.user.organization)
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

    def form_valid(self, form):
        form.instance.organization = self.request.user.organization
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
        if self.request.user.organization:
            qs = qs.filter(organization=self.request.user.organization)
        return qs

    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_officers:
            messages.error(request, 'Permission denied.')
            return redirect('officers:position_list')
        return super().dispatch(request, *args, **kwargs)

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
        if self.request.user.organization:
            qs = qs.filter(organization=self.request.user.organization)
        return qs

    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_officers:
            messages.error(request, 'Access denied. Only Super Admin can delete positions.')
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
        self.object = self.get_object()
        position_title = self.object.title
        position_pk = self.object.pk
        self.object.delete()
        from core.services.audit import log_activity
        log_activity(request, 'POSITION_DELETE', f"Deleted position '{position_title}'", resource_type='Position', resource_id=position_pk)
        messages.success(request, f"Position '{position_title}' has been deleted. Affected officers' positions have been cleared.")
        return redirect(self.success_url)
