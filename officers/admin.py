from django.contrib import admin
from .models import Position, Officer


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at']
    search_fields = ['title']


@admin.register(Officer)
class OfficerAdmin(admin.ModelAdmin):
    list_display = ['user', 'position', 'student_id']
    list_filter = ['position']
    search_fields = ['user__first_name', 'user__last_name', 'student_id']
