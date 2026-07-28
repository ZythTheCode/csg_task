from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('org_admin', 'Organization Admin'),
        ('president', 'President'),
        ('executive', 'Executive Officer'),
        ('committee_head', 'Committee Head'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='committee_head')
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users'
    )
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def position_title(self):
        if hasattr(self, 'officer_profile') and self.officer_profile and self.officer_profile.position:
            return self.officer_profile.position.title
        return self.get_role_display() or 'Officer'

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'

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
    def can_manage_tasks(self):
        return self.role in ['super_admin', 'org_admin']

    @property
    def can_view_reports(self):
        return self.role in ['super_admin', 'org_admin', 'president']

    @property
    def can_manage_officers(self):
        return self.role in ['super_admin', 'org_admin']
