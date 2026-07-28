from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.utils.translation import gettext_lazy as _
from .models import User


class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(_("There is no active user associated with this email address."))
        return email


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'bio', 'profile_picture']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }
