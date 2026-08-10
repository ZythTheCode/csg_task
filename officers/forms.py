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

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if title.lower() == 'president':
            org = getattr(self.instance, 'organization', None)
            if not org and self.request and hasattr(self.request.user, 'get_organization'):
                org = self.request.user.get_organization(self.request)
            if org:
                existing = Position.objects.filter(organization=org, title__iexact='president')
                if self.instance and self.instance.pk:
                    existing = existing.exclude(pk=self.instance.pk)
                if existing.exists():
                    raise forms.ValidationError("A position titled 'President' already exists for this organization. Only one President position is allowed per organization.")
        return title


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
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 202612345'}),
        }

    def __init__(self, *args, user=None, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_creator = user
        self.request = request

        # Determine target organization based on request active workspace, user_creator, or officer instance
        target_org = None
        if self.request and hasattr(self.request.user, 'get_organization'):
            target_org = self.request.user.get_organization(self.request)
        elif self.user_creator and hasattr(self.user_creator, 'get_organization'):
            target_org = self.user_creator.get_organization()
        elif self.user_creator:
            target_org = getattr(self.user_creator, 'organization', None)

        if not target_org and self.instance and self.instance.pk and getattr(self.instance, 'user', None):
            target_org = self.instance.user.organization

        self.target_org = target_org

        # Build position choices showing assigned officer names and disabled state
        from .models import Position as PositionModel
        all_positions = PositionModel.objects.all()
        if target_org:
            all_positions = all_positions.filter(organization=target_org)
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

        choices = [('', 'Select Position')]
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
            required=True,
            initial=initial_position_id,
            error_messages={'required': 'Assigning a position is required.'},
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
            raise forms.ValidationError("Assigning a position is required.")
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

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        position_obj = cleaned_data.get('position')

        org = getattr(self, 'target_org', None)
        if not org and self.user_creator and hasattr(self.user_creator, 'get_organization'):
            org = self.user_creator.get_organization(self.request)
        if not org and self.instance and self.instance.pk and getattr(self.instance, 'user', None):
            org = self.instance.user.organization

        is_pres_role = (role == 'president')
        is_pres_position = False
        if position_obj and position_obj.title.strip().lower() == 'president':
            is_pres_position = True

        if is_pres_position:
            cleaned_data['role'] = 'president'
            role = 'president'

        if (is_pres_role or is_pres_position) and org:
            # Check 1: User with role 'president' in this org
            existing_pres_user = User.objects.filter(organization=org, role='president', is_active=True)
            if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
                existing_pres_user = existing_pres_user.exclude(pk=self.instance.user.pk)

            if existing_pres_user.exists():
                pres_user = existing_pres_user.first()
                pres_name = pres_user.get_full_name() or pres_user.username
                raise forms.ValidationError(
                    f"This organization already has a President ({pres_name}). An organization can only have one President."
                )

            # Check 2: Officer with position titled 'President' in this org
            existing_pres_officer = Officer.objects.filter(
                user__organization=org,
                position__title__iexact='President'
            )
            if self.instance and self.instance.pk:
                existing_pres_officer = existing_pres_officer.exclude(pk=self.instance.pk)

            if existing_pres_officer.exists():
                pres_officer = existing_pres_officer.first()
                pres_name = pres_officer.user.get_full_name() or pres_officer.user.username
                raise forms.ValidationError(
                    f"This organization already has an officer assigned as President ({pres_name}). An organization can only have one President."
                )

        return cleaned_data

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

        target_org = getattr(self, 'target_org', None)

        if officer.pk and getattr(officer, 'user', None):
            user = officer.user
            user.first_name = first_name
            user.last_name = last_name
            user.username = username
            user.email = email
            user.role = role
            if password:
                user.set_password(password)
            if target_org and not user.organization:
                user.organization = target_org
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
            if target_org:
                user.organization = target_org
            if self.cleaned_data.get('profile_picture'):
                user.profile_picture = self.cleaned_data.get('profile_picture')
            user.save()
            officer.user = user

        if commit:
            officer.save()
        return officer

