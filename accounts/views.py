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

    def get_success_url(self):
        return reverse_lazy('core:dashboard')


class CustomLogoutView(LogoutView):
    next_page = 'accounts:login'


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
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
