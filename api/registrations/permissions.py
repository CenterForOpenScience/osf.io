# -*- coding: utf-8 -*-
from rest_framework import permissions

from api.base.utils import get_user_auth

class ContributorOrModerator(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)

        if obj.provider.get_group('moderator').user_set.filter(id=request.user.id).exists():
                is_moderator = True

        return obj.is_admin_contributor(auth.user) or is_moderator
