from django.db import models
from django.conf import settings
from django.utils import timezone


class Task(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('processing', 'Processing'),
        ('to_advisers', 'To Advisers'),
        ('accounting', 'Accounting'),
        ('oca', 'OCA'),
        ('osas', 'OSAS'),
        ('ppss', 'PPSS'),
        ('supply', 'Supply'),
        ('completed', 'Completed'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    STATUS_COLORS = {
        'not_started': 'secondary',
        'processing': 'info',
        'to_advisers': 'primary',
        'accounting': 'warning',
        'oca': 'purple',
        'osas': 'indigo',
        'ppss': 'teal',
        'supply': 'orange',
        'completed': 'success',
    }
    PRIORITY_COLORS = {
        'low': 'success',
        'medium': 'warning',
        'high': 'danger',
        'urgent': 'dark',
    }

    task_number = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started', db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    completion_date = models.DateField(null=True, blank=True)
    progress = models.IntegerField(default=0)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
        db_index=True
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tasks')
    assigned_officers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='TaskAssignment',
        through_fields=('task', 'officer'),
        related_name='assigned_tasks',
        blank=True
    )
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status', 'is_archived']),
            models.Index(fields=['organization', 'due_date']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"[{self.task_number}] {self.title}"

    def save(self, *args, **kwargs):
        if self.status == 'completed':
            self.progress = 100
            
        if not self.task_number:
            year = timezone.now().year
            last = Task.objects.filter(task_number__startswith=f'{year}-').order_by('-task_number').first()
            if last:
                try:
                    seq = int(last.task_number.split('-')[-1]) + 1
                except ValueError:
                    seq = 1
            else:
                seq = 1
            self.task_number = f'{year}-{seq:04d}'
        super().save(*args, **kwargs)

    @property
    def status_color(self):
        return self.STATUS_COLORS.get(self.status, 'secondary')

    @property
    def priority_color(self):
        return self.PRIORITY_COLORS.get(self.priority, 'secondary')

    @property
    def is_overdue(self):
        if self.due_date and self.status not in ['completed', 'cancelled']:
            return self.due_date < timezone.now().date()
        return False

    @property
    def progress_color(self):
        if self.progress >= 100:
            return 'success'
        elif self.progress >= 75:
            return 'primary'
        elif self.progress >= 50:
            return 'info'
        elif self.progress >= 25:
            return 'warning'
        return 'danger'

    @property
    def sorted_assigned_officers(self):
        ORDER_MAP = {
            "President": 1,
            "Vice President": 2,
            "Secretary": 3,
            "Treasurer": 4,
            "Auditor": 5,
            "P.R.O.": 6,
            "Business Manager": 7,
            "Executive Assistant": 8,
            "Assistant Secretary": 9,
            "Assistant Treasurer": 10,
            "Events Manager": 11,
            "Graphics and Media": 12,
            "P.V.": 13,
        }
        officers = list(self.assigned_officers.all())
        officers.sort(key=lambda u: ORDER_MAP.get(u.position_title, 99))
        return officers


class TaskAssignment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='assignments')
    officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='assignments_made'
    )

    class Meta:
        unique_together = ('task', 'officer')

    def __str__(self):
        return f"{self.officer.get_full_name()} → {self.task.title}"


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.get_full_name()} on {self.task.title}"


def get_task_attachment_storage():
    try:
        from django.conf import settings
        if 'cloudinary_storage' in getattr(settings, 'INSTALLED_APPS', []):
            from core.storage import SmartRawMediaCloudinaryStorage
            return SmartRawMediaCloudinaryStorage()
    except Exception:
        pass
    return None


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/', storage=get_task_attachment_storage)
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename


class TaskHistory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    field_changed = models.CharField(max_length=50)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.task.task_number} - {self.field_changed} changed"
