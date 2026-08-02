from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from .models import User
from . import forms


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        from core.services.audit import log_activity
        user = form.get_user()
        log_activity(self.request, 'USER_LOGIN', f"User '{user.username}' logged in successfully.", resource_type='User', resource_id=user.pk)
        return super().form_valid(form)

    def form_invalid(self, form):
        from core.services.audit import log_activity
        log_activity(self.request, 'USER_LOGIN_FAILED', "Failed login attempt.", status='failed')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('core:dashboard')


class CustomLogoutView(LogoutView):
    next_page = 'accounts:login'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            from core.services.audit import log_activity
            log_activity(request, 'USER_LOGOUT', f"User '{request.user.username}' logged out.", resource_type='User', resource_id=request.user.pk)
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        from core.services.audit import log_activity
        log_activity(self.request, 'PASSWORD_CHANGE', "User changed password successfully.", resource_type='User', resource_id=self.request.user.pk)
        messages.success(self.request, 'Password changed successfully.')
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'My Profile'
        try:
            ctx['officer'] = self.request.user.officer_profile
        except Exception:
            ctx['officer'] = None
        return ctx


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = forms.ProfileEditForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully.')
        return super().form_valid(form)


from django.http import JsonResponse
from django.views import View

class ToggleDarkModeView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        requested_mode = request.POST.get('mode')
        if requested_mode in ['dark', 'light']:
            user.dark_mode = (requested_mode == 'dark')
        else:
            user.dark_mode = not user.dark_mode
        user.save(update_fields=['dark_mode'])
        return JsonResponse({'status': 'ok', 'dark_mode': user.dark_mode})

