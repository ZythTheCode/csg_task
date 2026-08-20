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

        # Reject if new password is same as current password
        new_password = form.cleaned_data.get('new_password1')
        if new_password and self.request.user.check_password(new_password):
            is_ajax = self.request.headers.get('x-requested-with') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'errors': {'new_password1': ['New password must be different from your current password.']}
                }, status=400)
            form.add_error('new_password1', 'New password must be different from your current password.')
            return self.form_invalid(form)

        form.save()
        log_activity(self.request, 'PASSWORD_CHANGE', "User changed password successfully.", resource_type='User', resource_id=self.request.user.pk)
        messages.success(self.request, 'Password changed successfully.')

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'message': 'Password changed successfully.'})

        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            error_dict = {}
            for field, errors in form.errors.items():
                error_dict[field] = [str(e) for e in errors]
            return JsonResponse({'status': 'error', 'errors': error_dict}, status=400)
        return super().form_invalid(form)


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

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST.get('action') == 'remove_photo':
            if self.object.profile_picture:
                self.object.profile_picture.delete(save=False)
                self.object.profile_picture = None
                self.object.save(update_fields=['profile_picture'])
                from core.services.audit import log_activity
                log_activity(request, 'PROFILE_PHOTO_REMOVE', "Removed profile photo and reverted to default avatar.", resource_type='User', resource_id=self.object.pk)
                messages.success(request, 'Profile picture removed successfully.')
            return redirect('accounts:profile')
        return super().post(request, *args, **kwargs)

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

