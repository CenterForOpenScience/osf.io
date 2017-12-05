# -*- coding: utf-8 -*-
from rest_framework import permissions
from admin.base import settings

class IsOsfAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user and user.has_perm('osf.osf_admin')


class IsAdminOrFromAdminApp(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.META.get('HTTP_X_ADMIN') == settings.ADMIN_API_SECRET:
            return True
        user = request.user
        return user and user.has_perm('osf.change_node')
