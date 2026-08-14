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


class DisabledRoleSelect(forms.Select):
    def __init__(self, attrs=None, choices=(), disabled_choices=()):
        super().__init__(attrs, choices)
        self.disabled_choices = set(disabled_choices)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if str(value) in self.disabled_choices:
            option['attrs']['disabled'] = 'disabled'
        return option


class DisabledPositionSelect(forms.Select):
    def __init__(self, attrs=None, choices=(), disabled_choices=()):
        super().__init__(attrs, choices)
        self.disabled_choices = set(disabled_choices)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if str(value) in self.disabled_choices:
            option['attrs']['disabled'] = 'disabled'
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
        from organizations.models import Organization
        target_org = None
        if self.request and hasattr(self.request.user, 'get_organization'):
            target_org = self.request.user.get_organization(self.request)
        elif self.user_creator and hasattr(self.user_creator, 'get_organization'):
            target_org = self.user_creator.get_organization()
        elif self.user_creator:
            target_org = getattr(self.user_creator, 'organization', None)

        if not target_org and self.instance and self.instance.pk and getattr(self.instance, 'user', None):
            target_org = self.instance.user.organization

        if not target_org:
            target_org = Organization.objects.filter(abbreviation='CSG').first() or Organization.objects.first()

        self.target_org = target_org

        # Optional organization select for Super Admin
        is_super = False
        if self.request and hasattr(self.request.user, 'is_super_admin'):
            is_super = self.request.user.is_super_admin
        elif self.user_creator and hasattr(self.user_creator, 'is_super_admin'):
            is_super = self.user_creator.is_super_admin

        if is_super:
            org_qs = Organization.objects.all().order_by('name')
            org_choices = [(org.pk, f"{org.name} ({org.abbreviation})") for org in org_qs]
            self.fields['organization'] = forms.ChoiceField(
                choices=org_choices,
                required=False,
                initial=target_org.pk if target_org else None,
                widget=forms.Select(attrs={'class': 'form-select'})
            )

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

        choices = [('', 'Select Position (Optional)')]
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

        # Check if an Org Admin or President already exists in this target_org
        self.disabled_role_codes = set()
        org_admin_user = None
        president_user = None
        if target_org:
            existing_org_admin = User.objects.filter(organization=target_org, role='org_admin', is_active=True)
            if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
                existing_org_admin = existing_org_admin.exclude(pk=self.instance.user.pk)
            if existing_org_admin.exists():
                org_admin_user = existing_org_admin.first()
                self.disabled_role_codes.add('org_admin')

            existing_president = User.objects.filter(organization=target_org, role='president', is_active=True)
            if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
                existing_president = existing_president.exclude(pk=self.instance.user.pk)
            if existing_president.exists():
                president_user = existing_president.first()
                self.disabled_role_codes.add('president')

        # Define role choices
        role_choices = []
        if 'org_admin' in self.disabled_role_codes and org_admin_user:
            admin_name = org_admin_user.get_full_name() or org_admin_user.username
            role_choices.append(('org_admin', f"Org Admin ({admin_name})"))
        else:
            role_choices.append(('org_admin', 'Org Admin'))

        if 'president' in self.disabled_role_codes and president_user:
            pres_name = president_user.get_full_name() or president_user.username
            role_choices.append(('president', f"President ({pres_name})"))
        else:
            role_choices.append(('president', 'President'))

        role_choices.append(('executive', 'Elected Officer'))
        role_choices.append(('committee_head', 'Committee Member'))

        initial_role = None
        if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
            initial_role = self.instance.user.role
        else:
            initial_role = 'executive' if 'org_admin' in self.disabled_role_codes else 'org_admin'

        self.fields['role'] = forms.ChoiceField(
            choices=role_choices,
            required=True,
            initial=initial_role,
            widget=DisabledRoleSelect(
                attrs={'class': 'form-select'},
                disabled_choices=self.disabled_role_codes
            )
        )

        if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
            user = self.instance.user
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email
            self.fields['role'].initial = user.role
            self.fields['profile_picture'].initial = user.profile_picture

    def clean_username(self):
        val = self.cleaned_data.get('username')
        username = val.strip() if val else ''
        if username:
            qs = User.objects.filter(username__iexact=username)
            if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
                qs = qs.exclude(pk=self.instance.user.pk)
            if qs.exists():
                raise forms.ValidationError("This username is already taken. Please choose another username.")
        return username

    def clean_student_id(self):
        val = self.cleaned_data.get('student_id')
        student_id = val.strip() if val else ''
        if student_id:
            qs = Officer.objects.filter(student_id__iexact=student_id)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This Student ID is already registered to an existing officer.")
            return student_id
        return None

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

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')

        selected_org_pk = cleaned_data.get('organization')
        if selected_org_pk:
            from organizations.models import Organization
            try:
                self.target_org = Organization.objects.get(pk=selected_org_pk)
            except Organization.DoesNotExist:
                pass

        org = getattr(self, 'target_org', None)
        if not org and self.user_creator and hasattr(self.user_creator, 'get_organization'):
            org = self.user_creator.get_organization(self.request)
        if not org and self.instance and self.instance.pk and getattr(self.instance, 'user', None):
            org = self.instance.user.organization

        if role == 'org_admin' and org:
            existing_admin = User.objects.filter(organization=org, role='org_admin', is_active=True)
            if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
                existing_admin = existing_admin.exclude(pk=self.instance.user.pk)

            if existing_admin.exists():
                admin_user = existing_admin.first()
                admin_name = admin_user.get_full_name() or admin_user.username
                raise forms.ValidationError(
                    f"This organization already has an Org Admin ({admin_name}). An organization can only have one Org Admin."
                )

        if role == 'president' and org:
            existing_pres = User.objects.filter(organization=org, role='president', is_active=True)
            if self.instance and self.instance.pk and getattr(self.instance, 'user', None):
                existing_pres = existing_pres.exclude(pk=self.instance.user.pk)

            if existing_pres.exists():
                pres_user = existing_pres.first()
                pres_name = pres_user.get_full_name() or pres_user.username
                raise forms.ValidationError(
                    f"This organization already has a President ({pres_name}). An organization can only have one President."
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
            existing_user_id = None
            if officer.pk and hasattr(officer, 'user'):
                try:
                    if officer.user:
                        existing_user_id = officer.user.pk
                except Exception:
                    pass

            while User.objects.filter(username=username).exclude(pk=existing_user_id).exists():
                username = f"{base_uname}{count}"
                count += 1

        target_org = getattr(self, 'target_org', None)
        if not target_org:
            from organizations.models import Organization
            target_org = Organization.objects.filter(abbreviation='CSG').first() or Organization.objects.first()

        if officer.pk and hasattr(officer, 'user'):
            try:
                user = officer.user
                user.first_name = first_name
                user.last_name = last_name
                user.username = username
                user.email = email
                user.role = role
                if password:
                    user.set_password(password)
                if target_org:
                    user.organization = target_org
                if 'profile_picture' in self.changed_data:
                    user.profile_picture = self.cleaned_data.get('profile_picture')
                user.save()
            except Exception:
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

