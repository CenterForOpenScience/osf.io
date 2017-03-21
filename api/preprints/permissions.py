# -*- coding: utf-8 -*-
from rest_framework import permissions

from api.base.utils import get_user_auth
from website.models import PreprintService
from website.util import permissions as osf_permissions


class PreprintPublishedOrAdmin(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, PreprintService), 'obj must be a PreprintService'
        node = obj.node
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_published or node.has_permission(auth.user, osf_permissions.ADMIN)
        else:
            return node.has_permission(auth.user, osf_permissions.ADMIN)
