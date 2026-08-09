from django import forms
from .models import Position, Officer
from accounts.models import User


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['title', 'initials', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_title', 'placeholder': 'e.g. Vice President'}),
            'initials': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_initials', 'placeholder': 'Auto-generated (e.g. VP) or custom'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DisabledPositionSelect(forms.Select):
    def __init__(self, attrs=None, choices=(), disabled_choices=()):
        super().__init__(attrs, choices)
        self.disabled_choices = set(str(x) for x in disabled_choices)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and str(value) in self.disabled_choices:
            option['attrs']['disabled'] = True
        return option


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
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2024-0001'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_creator = user

        # Build position choices showing assigned officer names and disabled state
        from .models import Position as PositionModel
        all_positions = PositionModel.objects.all()
        if self.user_creator and self.user_creator.organization:
            all_positions = all_positions.filter(organization=self.user_creator.organization)
        all_positions = all_positions.select_related('officer__user').order_by('title')

        assigned_map = {}
        for pos in all_positions:
            try:
                officer = pos.officer
                if self.instance and self.instance.pk and officer.pk == self.instance.pk:
                    continue
                if officer and getattr(officer, 'user', None):
                    full_name = officer.user.get_full_name() or officer.user.username
                    assigned_map[pos.pk] = full_name
            except Officer.DoesNotExist:
                pass

        choices = [('', '---------')]
        self.disabled_position_pks = set()

        for pos in all_positions:
            if pos.pk in assigned_map:
                officer_name = assigned_map[pos.pk]
                label = f"{pos.title} ({officer_name})"
                choices.append((pos.pk, label))
                self.disabled_position_pks.add(str(pos.pk))
            else:
                label = pos.title
                choices.append((pos.pk, label))

        initial_position_id = self.instance.position_id if (self.instance and self.instance.pk) else None

        self.fields['position'] = forms.ChoiceField(
            choices=choices,
            required=False,
            initial=initial_position_id,
            widget=DisabledPositionSelect(
                attrs={'class': 'form-select'},
                disabled_choices=self.disabled_position_pks
            )
        )

        # Restrict role choices
        allowed_roles = []
        for code, label in User.ROLE_CHOICES:
            if code in ['super_admin', 'org_admin', 'super_super_admin']:
                continue
            allowed_roles.append((code, label))
            
        if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
            user = self.instance.user
            if not any(c == user.role for c, l in allowed_roles):
                allowed_roles.append((user.role, dict(User.ROLE_CHOICES).get(user.role, user.role)))
        
        self.fields['role'].choices = allowed_roles

        if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
            user = self.instance.user
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email
            self.fields['role'].initial = user.role
            self.fields['profile_picture'].initial = user.profile_picture

    def clean_position(self):
        position_val = self.cleaned_data.get('position')
        if not position_val:
            return None
        if isinstance(position_val, Position):
            position_obj = position_val
        else:
            try:
                position_obj = Position.objects.get(pk=position_val)
            except Position.DoesNotExist:
                raise forms.ValidationError("Invalid position selected.")

        if hasattr(self, 'disabled_position_pks') and str(position_obj.pk) in self.disabled_position_pks:
            raise forms.ValidationError("This position is already assigned to another officer.")

        return position_obj

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

