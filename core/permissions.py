from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import permissions


class TenantScopedQuerySetMixin(LoginRequiredMixin):
    """
    QuerySet mixin ensuring queries automatically filter by the user's organization.
    Super Admins can view across all organizations.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_super_admin:
            return qs
        if hasattr(qs.model, 'organization'):
            return qs.filter(organization=user.organization)
        elif hasattr(qs.model, 'user') and hasattr(qs.model.user.field.related_model, 'organization'):
            return qs.filter(user__organization=user.organization)
        return qs


class TenantObjectPermissionMixin(TenantScopedQuerySetMixin):
    """
    Object-level mixin preventing Cross-Tenant IDOR access.
    Raises PermissionDenied if the requested object belongs to another tenant.
    """
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.is_super_admin:
            return obj
        
        obj_org = getattr(obj, 'organization', None)
        if obj_org is None and hasattr(obj, 'user'):
            obj_org = getattr(obj.user, 'organization', None)
            
        if obj_org and user.organization and obj_org != user.organization:
            raise PermissionDenied("You do not have permission to access resources outside your organization.")
        return obj


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Role permission mixin checking specific permission flags on the User model.
    """
    required_permission_attribute = None  # e.g., 'can_manage_tasks', 'can_manage_officers', 'can_view_reports', 'is_super_admin'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if self.required_permission_attribute:
            has_perm = getattr(request.user, self.required_permission_attribute, False)
            if callable(has_perm):
                has_perm = has_perm()
            if not has_perm:
                raise PermissionDenied("You do not have sufficient permissions to access this page.")
        return super().dispatch(request, *args, **kwargs)


class IsSameOrganizationPermission(permissions.BasePermission):
    """
    DRF Permission class enforcing tenant boundary for API endpoints.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_super_admin:
            return True
        obj_org = getattr(obj, 'organization', None)
        if obj_org is None and hasattr(obj, 'user'):
            obj_org = getattr(obj.user, 'organization', None)
        return obj_org == request.user.organization


class IsOrgAdminPermission(permissions.BasePermission):
    """
    DRF Permission class requiring Organization Admin or Super Admin role.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (request.user.is_org_admin or request.user.is_super_admin)


class CanManageTasksPermission(permissions.BasePermission):
    """
    DRF Permission class checking if user has task CRUD management permissions.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_manage_tasks
