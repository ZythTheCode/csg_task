from django.db import models
from django.conf import settings


class Position(models.Model):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='positions'
    )
    title = models.CharField(max_length=100)
    initials = models.CharField(max_length=20, blank=True, help_text="Default or custom initials for position")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def get_initials(self):
        if self.initials and self.initials.strip():
            return self.initials.strip()
        from tasks.templatetags.task_filters import ABBREVIATIONS
        lower = self.title.lower().strip()
        if lower in ABBREVIATIONS:
            return ABBREVIATIONS[lower]
        words = self.title.split()
        if len(words) == 1:
            return self.title[:4].upper()
        return ''.join(w[0].upper() for w in words if w)

    def save(self, *args, **kwargs):
        if not self.initials or not self.initials.strip():
            self.initials = self.get_initials()
        super().save(*args, **kwargs)


class Officer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='officer_profile')
    position = models.OneToOneField(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name='officer')
    student_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.position}"

    def completed_tasks(self):
        if hasattr(self, 'annotated_completed'):
            return self.annotated_completed
        from tasks.models import TaskAssignment
        return TaskAssignment.objects.filter(officer=self.user, task__status='completed').count()

    def active_tasks(self):
        if hasattr(self, 'annotated_active'):
            return self.annotated_active
        from tasks.models import TaskAssignment
        return TaskAssignment.objects.filter(officer=self.user, task__status__in=['not_started', 'processing', 'to_advisers', 'accounting', 'oca', 'osas', 'ppss', 'supply']).count()

    def total_tasks(self):
        if hasattr(self, 'annotated_total'):
            return self.annotated_total
        from tasks.models import TaskAssignment
        return TaskAssignment.objects.filter(officer=self.user).count()
