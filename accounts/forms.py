from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.utils.translation import gettext_lazy as _
from .models import User


class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        email = email.strip() if email else ''
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(_("There is no active user associated with this email address."))
        return email

    def get_users(self, email):
        """
        Return all active users matching the given email address regardless of
        whether has_usable_password() is True or False, ensuring accounts created
        by admins can still request password resets.
        """
        email = email.strip() if email else ''
        email_field_name = User.get_email_field_name()
        active_users = User._default_manager.filter(
            **{
                "%s__iexact" % email_field_name: email,
                "is_active": True,
            }
        )
        return active_users

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        from django.conf import settings
        from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None) or 'csgtasks2026@gmail.com'
        html_email_template_name = html_email_template_name or email_template_name
        try:
            super().send_mail(
                subject_template_name=subject_template_name,
                email_template_name=email_template_name,
                context=context,
                from_email=from_email,
                to_email=to_email,
                html_email_template_name=html_email_template_name,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send password reset email to {to_email}: {e}")



class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'bio', 'profile_picture']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }
