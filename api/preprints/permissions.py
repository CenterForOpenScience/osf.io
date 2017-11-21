# -*- coding: utf-8 -*-
from rest_framework import permissions
from rest_framework import exceptions

from api.base.utils import get_user_auth
from osf.models import PreprintService
from osf.utils.workflows import DefaultStates
from website.util import permissions as osf_permissions


class PreprintPublishedOrAdmin(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, PreprintService), 'obj must be a PreprintService'
        node = obj.node
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            if auth.user is None:
                return obj.verified_publishable
            else:
                user_has_permissions = (obj.verified_publishable or
                    (node.is_public and auth.user.has_perm('view_submissions', obj.provider)) or
                    node.has_permission(auth.user, osf_permissions.ADMIN) or
                    (node.is_contributor(auth.user) and obj.machine_state != DefaultStates.INITIAL.value)
                )
                return user_has_permissions
        else:
            if not node.has_permission(auth.user, osf_permissions.ADMIN):
                raise exceptions.PermissionDenied(detail='User must be an admin to update a preprint.')
            return True
