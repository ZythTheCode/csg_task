from django import forms
from .models import Organization
from accounts.models import User

class OrganizationRegistrationForm(forms.ModelForm):
    admin_first_name = forms.CharField(max_length=150, label='Admin First Name')
    admin_last_name = forms.CharField(max_length=150, label='Admin Last Name')
    admin_email = forms.EmailField(label='Admin Email')
    admin_student_id = forms.CharField(max_length=20, label='Admin Student ID')
    admin_username = forms.CharField(max_length=150, label='Admin Username')
    admin_password = forms.CharField(widget=forms.PasswordInput, label='Admin Password')

    class Meta:
        model = Organization
        fields = ['name', 'abbreviation', 'description']

    def clean_admin_username(self):
        username = self.cleaned_data.get('admin_username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_admin_email(self):
        email = self.cleaned_data.get('admin_email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def save(self, commit=True):
        org = super().save(commit=False)
        org.status = 'pending'
        if commit:
            org.save()
            # Create the admin user
            user = User.objects.create_user(
                username=self.cleaned_data['admin_username'],
                email=self.cleaned_data['admin_email'],
                password=self.cleaned_data['admin_password'],
                first_name=self.cleaned_data['admin_first_name'],
                last_name=self.cleaned_data['admin_last_name'],
                role='org_admin',
                organization=org,
                is_active=False  # Wait for approval
            )
            # You might want to create an Officer record for them as well, depending on how officers are handled.
            from officers.models import Officer, Position
            # We can create a default 'President' position for this org
            pos, _ = Position.objects.get_or_create(title='President', organization=org)
            Officer.objects.create(
                user=user,
                student_id=self.cleaned_data['admin_student_id'],
                position=pos
            )
        return org
