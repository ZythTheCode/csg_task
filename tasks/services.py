from django.db import models, transaction
from django.utils import timezone
from tasks.models import Task, TaskAssignment, TaskHistory, TaskAttachment, TaskComment
from core.services.audit import log_activity


class TaskService:
    @staticmethod
    @transaction.atomic
    def create_task(user, title, description, category='document', priority='medium', status='not_started', due_date=None, progress=0, assigned_officer_ids=None, organization=None):
        org = organization or user.organization
        task = Task.objects.create(
            title=title,
            description=description,
            category=category,
            priority=priority,
            status=status,
            due_date=due_date,
            progress=progress,
            organization=org,
            created_by=user
        )

        if assigned_officer_ids:
            for off_id in assigned_officer_ids:
                TaskAssignment.objects.create(
                    task=task,
                    officer_id=off_id,
                    assigned_by=user
                )

        TaskHistory.objects.create(
            task=task,
            changed_by=user,
            field_changed='Task Created',
            new_value=f"Status: {status}, Priority: {priority}"
        )

        log_activity(None, 'TASK_CREATE', f"Created task {task.task_number}: '{title}'", resource_type='Task', resource_id=task.id)
        return task

    @staticmethod
    @transaction.atomic
    def update_task_status(task, new_status, user, request=None):
        old_status = task.get_status_display()
        task.status = new_status
        if new_status == 'completed':
            task.progress = 100
            task.completion_date = timezone.now().date()
        task.save()

        TaskHistory.objects.create(
            task=task,
            changed_by=user,
            field_changed='status',
            old_value=old_status,
            new_value=task.get_status_display()
        )

        log_activity(request, 'TASK_STATUS_CHANGE', f"Task {task.task_number} moved from '{old_status}' to '{task.get_status_display()}'", resource_type='Task', resource_id=task.id)
        return task

    @staticmethod
    @transaction.atomic
    def bulk_delete_tasks(task_ids, user, request=None):
        tasks = Task.objects.filter(id__in=task_ids)
        org = user.get_organization(request)
        if org and not getattr(user, 'is_super_admin', False):
            tasks = tasks.filter(models.Q(organization=org) | models.Q(organization__isnull=True) | models.Q(created_by=user))

        count = tasks.count()
        task_numbers = list(tasks.values_list('task_number', flat=True))
        tasks.delete()

        log_activity(request, 'TASK_BULK_DELETE', f"Bulk deleted {count} tasks: {', '.join(task_numbers)}", resource_type='Task')
        return count

    @staticmethod
    def cleanup_expired_completed_tasks():
        import datetime
        today = timezone.now().date()
        cutoff_date = today - datetime.timedelta(days=7)
        expired = Task.objects.filter(
            status='completed',
            completion_date__isnull=False,
            completion_date__lte=cutoff_date
        )
        count = expired.count()
        if count > 0:
            expired.delete()
        return count
