# -*- coding: utf-8 -*-
from rest_framework import permissions

from api.base.utils import get_user_auth

class ContributorOrModerator(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)

        is_moderator = False
        if obj.provider:
            is_moderator = obj.provider.user_is_moderator(request.user)

        return obj.is_admin_contributor(auth.user) or is_moderator
