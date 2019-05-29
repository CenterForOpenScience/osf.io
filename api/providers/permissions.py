# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from guardian.shortcuts import get_perms
from rest_framework import permissions as drf_permissions

from api.base.utils import get_user_auth


class CanSetUpProvider(drf_permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in drf_permissions.SAFE_METHODS:
            return True
        auth = get_user_auth(request)
        return auth.user.has_perm('set_up_moderation', obj)

class CanAddModerator(drf_permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method != 'POST':
            return True
        auth = get_user_auth(request)
        return auth.user.has_perm('add_moderator', view.get_provider())

class CanDeleteModerator(drf_permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method != 'DELETE':
            return True
        auth = get_user_auth(request)
        provider = view.get_provider()
        return auth.user.has_perm('remove_moderator', provider) or auth.user._id == view.kwargs.get('moderator_id', '')

class CanUpdateModerator(drf_permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method not in ['PATCH', 'PUT']:
            return True
        auth = get_user_auth(request)
        return auth.user.has_perm('update_moderator', view.get_provider())

class MustBeModerator(drf_permissions.BasePermission):
    def has_permission(self, request, view):
        auth = get_user_auth(request)
        return bool(get_perms(auth.user, view.get_provider()))
