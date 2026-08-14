import os
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

def user_profile_picture_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if not ext or len(ext) > 6:
        ext = '.jpg'
    user_id = instance.username or instance.pk or 'user'
    short_uuid = uuid.uuid4().hex[:8]
    return f"profile_pics/user_{user_id}_{short_uuid}{ext}"


class User(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('org_admin', 'Org Admin'),
        ('president', 'President'),
        ('executive', 'Elected Officer'),
        ('committee_head', 'Committee Member'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='committee_head')
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users'
    )
    profile_picture = models.ImageField(upload_to=user_profile_picture_path, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    dark_mode = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def get_organization(self, request=None):
        if request and hasattr(request, 'session') and self.is_super_admin:
            active_org_id = request.session.get('active_org_id')
            if active_org_id:
                from organizations.models import Organization
                org = Organization.objects.filter(id=active_org_id).first()
                if org:
                    return org
        if self.is_super_admin:
            from organizations.models import Organization
            csg_org = Organization.objects.filter(models.Q(abbreviation='CSG') | models.Q(name__icontains='Central Student Government')).first()
            if csg_org:
                return csg_org
        return self.organization

    @property
    def position_title(self):
        if hasattr(self, 'officer_profile') and self.officer_profile and self.officer_profile.position:
            return self.officer_profile.position.title
        return self.get_role_display() or 'Officer'

    @property
    def position_initials(self):
        if hasattr(self, 'officer_profile') and self.officer_profile and self.officer_profile.position:
            return self.officer_profile.position.get_initials()
        from tasks.templatetags.task_filters import initials
        return initials(self.position_title)

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'

    @property
    def is_super_super_admin(self):
        return False

    @property
    def is_org_admin(self):
        return self.role == 'org_admin'

    @property
    def is_president(self):
        return self.role == 'president'

    @property
    def is_executive(self):
        return self.role == 'executive'

    @property
    def has_task_override(self):
        return self.role in ['super_admin', 'org_admin', 'president']

    @property
    def can_manage_tasks(self):
        return self.is_authenticated

    @property
    def can_view_reports(self):
        return self.is_authenticated

    def can_edit_task(self, task):
        if self.has_task_override:
            return True
        if task.created_by_id == self.id:
            return True
        if task.assigned_officers.filter(id=self.id).exists():
            return True
        return False

    def can_update_task_progress(self, task):
        if self.has_task_override:
            return True
        if task.created_by_id == self.id:
            return True
        if task.assigned_officers.filter(id=self.id).exists():
            return True
        return False

    def can_nudge_task(self, task):
        if not task or not task.assigned_officers.exists():
            return False
        if self.has_task_override:
            return True
        if task.created_by_id == self.id:
            return True
        if task.assigned_officers.filter(id=self.id).exists():
            return True
        return False

    @property
    def can_manage_officers(self):
        return self.role in ['super_admin', 'org_admin', 'president']

