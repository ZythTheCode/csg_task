from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('task_assigned', 'Task Assigned'),
        ('task_updated', 'Task Updated'),
        ('due_soon', 'Due Date Approaching'),
        ('overdue', 'Task Overdue'),
        ('task_completed', 'Task Completed'),
        ('approval_needed', 'Approval Needed'),
        ('system', 'System'),
    ]
    TYPE_ICONS = {
        'task_assigned': 'bi-clipboard-plus',
        'task_updated': 'bi-pencil-square',
        'due_soon': 'bi-clock-history',
        'overdue': 'bi-exclamation-triangle',
        'task_completed': 'bi-check-circle',
        'approval_needed': 'bi-hourglass-split',
        'system': 'bi-gear',
    }
    TYPE_COLORS = {
        'task_assigned': 'primary',
        'task_updated': 'info',
        'due_soon': 'warning',
        'overdue': 'danger',
        'task_completed': 'success',
        'approval_needed': 'warning',
        'system': 'secondary',
    }

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='system')
    is_read = models.BooleanField(default=False)
    related_task = models.ForeignKey('tasks.Task', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username}: {self.title}"

    @property
    def icon(self):
        return self.TYPE_ICONS.get(self.notification_type, 'bi-bell')

    @property
    def color(self):
        return self.TYPE_COLORS.get(self.notification_type, 'secondary')
