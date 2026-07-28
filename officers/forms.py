from django import forms
from .models import Position, Officer
from accounts.models import User


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class OfficerForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Auto-generated if left blank'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@csg.edu.ph'})
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        help_text="Leave blank when editing to keep current password unchanged."
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    class Meta:
        model = Officer
        fields = ['position', 'student_id']
        widgets = {
            'position': forms.Select(attrs={'class': 'form-select'}),
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2024-0001'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_creator = user
        self.fields['position'].required = False

        # Only show positions not already assigned to another officer.
        # If editing, always include the officer's current position.
        current_position_pk = None
        if self.instance and self.instance.pk:
            current_position_pk = self.instance.position_id

        # Positions that are taken by someone else
        taken_qs = Officer.objects.filter(position__isnull=False)
        if self.instance and self.instance.pk:
            taken_qs = taken_qs.exclude(pk=self.instance.pk)
        taken_ids = taken_qs.values_list('position_id', flat=True)

        from .models import Position as PositionModel
        available_qs = PositionModel.objects.exclude(pk__in=taken_ids)
        if self.user_creator and self.user_creator.organization:
            available_qs = available_qs.filter(organization=self.user_creator.organization)
        self.fields['position'].queryset = available_qs

        if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
            user = self.instance.user
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email
            self.fields['role'].initial = user.role
            self.fields['profile_picture'].initial = user.profile_picture

    def save(self, commit=True):
        officer = super().save(commit=False)
        first_name = self.cleaned_data.get('first_name')
        last_name = self.cleaned_data.get('last_name')
        username = self.cleaned_data.get('username')
        email = self.cleaned_data.get('email')
        role = self.cleaned_data.get('role')
        password = self.cleaned_data.get('password')

        if not username:
            base_uname = f"{first_name[0].lower()}{last_name.lower().replace(' ', '')}" if first_name and last_name else "user"
            username = base_uname
            count = 1
            existing_user_id = officer.user.pk if (officer.pk and getattr(officer, 'user', None)) else None
            while User.objects.filter(username=username).exclude(pk=existing_user_id).exists():
                username = f"{base_uname}{count}"
                count += 1

        if officer.pk and getattr(officer, 'user', None):
            user = officer.user
            user.first_name = first_name
            user.last_name = last_name
            user.username = username
            user.email = email
            user.role = role
            if password:
                user.set_password(password)
            if 'profile_picture' in self.changed_data:
                user.profile_picture = self.cleaned_data.get('profile_picture')
            user.save()
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password or 'admin123',
                first_name=first_name,
                last_name=last_name,
                role=role
            )
            if self.user_creator and getattr(self.user_creator, 'organization', None):
                user.organization = self.user_creator.organization
            if self.cleaned_data.get('profile_picture'):
                user.profile_picture = self.cleaned_data.get('profile_picture')
            user.save()
            officer.user = user

        if commit:
            officer.save()
        return officer

