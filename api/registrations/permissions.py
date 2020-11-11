# -*- coding: utf-8 -*-
from guardian.shortcuts import get_perms
from rest_framework import permissions

from api.base.utils import get_user_auth

class ContributorOrModerator(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)

        # If a user has perms on the provider, they must be a moderator or admin
        is_moderator = bool(get_perms(auth.user, obj.provider))
        return obj.is_admin_contributor(auth.user) or is_moderator
