# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import permissions as drf_permissions

from api.base.utils import get_user_auth
from osf.models.action import NodeRequestAction
from osf.models.mixins import RequestableMixin
from osf.models.node import Node
from osf.utils.workflows import DefaultTriggers
from website.util import permissions as osf_permissions


class NodeRequestPermission(drf_permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        if auth.user is None:
            return False

        target = None
        if isinstance(obj, NodeRequestAction):
            target = obj.target
            node = obj.target.target
            trigger = request.data.get('trigger', None)
        elif isinstance(obj, RequestableMixin):
            target = obj
            node = obj.target
            # Creating a Request is "submitting"
            trigger = request.data.get('trigger', DefaultTriggers.SUBMIT.value if request.method not in drf_permissions.SAFE_METHODS else None)
        elif isinstance(obj, Node):
            node = obj
            trigger = DefaultTriggers.SUBMIT.value if request.method not in drf_permissions.SAFE_METHODS else None
        else:
            raise ValueError('Not a request-related model: {}'.format(obj))

        if not node.access_requests_enabled:
            return False

        is_requester = target is not None and target.creator == auth.user or trigger == DefaultTriggers.SUBMIT.value
        is_node_admin = node.has_permission(auth.user, osf_permissions.ADMIN)
        has_view_permission = is_requester or is_node_admin

        if request.method in drf_permissions.SAFE_METHODS:
            # Requesters and node admins can view actions
            return has_view_permission
        else:
            if not has_view_permission:
                return False

            if trigger in [DefaultTriggers.ACCEPT.value, DefaultTriggers.REJECT.value]:
                # Node admins can only approve or reject requests
                return is_node_admin
            if trigger in [DefaultTriggers.EDIT_COMMENT.value, DefaultTriggers.SUBMIT.value]:
                # Requesters may not be contributors
                # Requesters may edit their comment or submit their request
                return is_requester and auth.user not in node.contributors
            return False
