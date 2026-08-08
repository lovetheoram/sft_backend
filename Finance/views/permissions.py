"""
=============================================================================
🛡️ CUSTOM DRF PERMISSIONS MODULE
=============================================================================
"""

from rest_framework.permissions import BasePermission


def is_super_admin(user):
    """Super Admin: role == 'admin' and not assigned to any flat."""
    return user.role == 'admin' and user.flat is None


def is_building_admin(user):
    """Building Admin: role == 'admin' and assigned to a flat/building."""
    return user.role == 'admin' and user.flat is not None


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and is_super_admin(request.user)


class IsBuildingAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and is_building_admin(request.user)


class IsAdminOrBuildingAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

    def has_object_permission(self, request, view, obj):
        if is_super_admin(request.user):
            return True
        if is_building_admin(request.user):
            user_building = getattr(getattr(request.user, 'flat', None), 'building', None)
            obj_building = getattr(obj, 'building', None)
            return user_building is not None and user_building == obj_building
        return False
