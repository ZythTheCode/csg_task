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
        import threading
        import logging

        from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None) or 'csgtasks2026@gmail.com'
        html_email_template_name = html_email_template_name or email_template_name
        
        def _send_email_task():
            try:
                super(CustomPasswordResetForm, self).send_mail(
                    subject_template_name=subject_template_name,
                    email_template_name=email_template_name,
                    context=context,
                    from_email=from_email,
                    to_email=to_email,
                    html_email_template_name=html_email_template_name,
                )
                logging.getLogger(__name__).info(f"Password reset email dispatched successfully to {to_email}")
            except Exception as e:
                logging.getLogger(__name__).error(f"CRITICAL SMTP ERROR: Failed to send password reset email to {to_email}. Ensure EMAIL_HOST_PASSWORD (App Password) and EMAIL_HOST_USER are correct. Error: {str(e)}", exc_info=True)

        # Dispatch email sending to a background thread to prevent UI freezing/timeouts
        email_thread = threading.Thread(target=_send_email_task)
        email_thread.daemon = True
        email_thread.start()



class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'bio', 'profile_picture']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_email(self):
        val = self.cleaned_data.get('email')
        email = val.strip() if val else ''
        if email:
            qs = User.objects.filter(email__iexact=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This email is already registered to an existing account.")
        return email
