from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('CSG Profile', {'fields': ('role', 'profile_picture', 'phone', 'bio')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('CSG Profile', {'fields': ('role', 'first_name', 'last_name', 'email')}),
    )
