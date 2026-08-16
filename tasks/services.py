from django.db import models, transaction
from django.utils import timezone
from tasks.models import Task, TaskAssignment, TaskHistory, TaskAttachment, TaskComment
from notifications.models import Notification
from core.services.audit import log_activity


# Maximum number of tasks allowed per bulk operation
BULK_OPERATION_MAX_TASKS = 50


def bulk_complete_tasks(queryset, user):
    """
    Mark multiple tasks as completed using bulk operations.
    Returns (count, error) tuple where error is None on success.

    Uses at most 3 write queries:
    - 1 bulk_update for task fields (status, progress, completion_date)
    - 1 bulk_create for TaskHistory records
    - 1 bulk_create for Notification records

    All wrapped in transaction.atomic() for atomicity.
    Caps at BULK_OPERATION_MAX_TASKS tasks per request.
    Excludes already-completed tasks.
    """
    # Validate task count cap
    task_count = queryset.count()
    if task_count > BULK_OPERATION_MAX_TASKS:
        return 0, f"Maximum {BULK_OPERATION_MAX_TASKS} tasks per bulk operation. Got {task_count}."

    now_date = timezone.now().date()
    status_dict = dict(Task.STATUS_CHOICES)

    # Exclude already-completed tasks, prefetch assignments for notifications
    tasks = list(
        queryset.exclude(status='completed')
        .prefetch_related('assignments__officer')
    )

    if not tasks:
        return 0, None

    tasks_to_update = []
    history_records = []
    notification_records = []

    for task in tasks:
        old_status = task.status
        task.status = 'completed'
        task.completion_date = now_date
        task.progress = 100
        tasks_to_update.append(task)

        history_records.append(TaskHistory(
            task=task,
            changed_by=user,
            field_changed='Status',
            old_value=status_dict.get(old_status, old_status),
            new_value='Completed'
        ))

        for assignment in task.assignments.all():
            notification_records.append(Notification(
                recipient=assignment.officer,
                title='Task Completed',
                message=f'Task "{task.title}" has been marked as completed.',
                notification_type='task_completed',
                related_task=task
            ))

    try:
        with transaction.atomic():
            if tasks_to_update:
                Task.objects.bulk_update(
                    tasks_to_update,
                    fields=['status', 'completion_date', 'progress']
                )
            if history_records:
                TaskHistory.objects.bulk_create(history_records)
            if notification_records:
                Notification.objects.bulk_create(notification_records)
    except Exception as e:
        return 0, f"Operation did not complete: {str(e)}"

    return len(tasks_to_update), None


def bulk_reassign_officers(task, new_officers, assigned_by):
    """
    Reassign officers to a task using bulk operations.
    Single delete + bulk_create within a transaction.

    Returns (count, error) tuple where count is the number of new assignments created.
    """
    try:
        with transaction.atomic():
            TaskAssignment.objects.filter(task=task).delete()
            assignments = [
                TaskAssignment(task=task, officer=officer, assigned_by=assigned_by)
                for officer in new_officers
            ]
            if assignments:
                TaskAssignment.objects.bulk_create(assignments)
    except Exception as e:
        return 0, f"Operation did not complete: {str(e)}"

    return len(assignments) if new_officers else 0, None


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
