from django.db import models
from django.conf import settings


class Position(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class Officer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='officer_profile')
    position = models.OneToOneField(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name='officer')
    student_id = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.position}"

    def completed_tasks(self):
        from tasks.models import TaskAssignment
        return TaskAssignment.objects.filter(officer=self.user, task__status='completed').count()

    def active_tasks(self):
        from tasks.models import TaskAssignment
        return TaskAssignment.objects.filter(officer=self.user, task__status__in=['not_started', 'processing', 'to_advisers', 'accounting', 'oca', 'osas', 'ppss', 'supply']).count()

    def total_tasks(self):
        from tasks.models import TaskAssignment
        return TaskAssignment.objects.filter(officer=self.user).count()
