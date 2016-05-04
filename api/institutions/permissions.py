# -*- coding: utf-8 -*-
from rest_framework import permissions

from api.base.utils import get_user_auth

class UserIsAffiliated(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, dict)
        user = get_user_auth().user

        if request.method in permissions.SAFE_METHODS or request.method == 'DELETE':
            return True
        else:
            return obj['self'] in user.affiliated_institutions
