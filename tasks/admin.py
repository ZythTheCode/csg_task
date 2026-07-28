from django.contrib import admin
from .models import Task, TaskAssignment, TaskComment, TaskAttachment, TaskHistory


class TaskAssignmentInline(admin.TabularInline):
    model = TaskAssignment
    extra = 1


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['task_number', 'title', 'status', 'priority', 'due_date', 'created_by']
    list_filter = ['status', 'priority', 'is_archived']
    search_fields = ['title', 'task_number', 'description']
    inlines = [TaskAssignmentInline, TaskCommentInline]
    readonly_fields = ['task_number', 'created_at', 'updated_at']


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ['task', 'field_changed', 'changed_by', 'timestamp']
    list_filter = ['field_changed']
    readonly_fields = ['task', 'changed_by', 'field_changed', 'old_value', 'new_value', 'timestamp']
