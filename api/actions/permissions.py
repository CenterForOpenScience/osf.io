# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import permissions as drf_permissions

from api.base.utils import get_user_auth
from osf.models.action import ReviewAction
from osf.models.mixins import ReviewableMixin, ReviewProviderMixin
from osf.utils.workflows import DefaultTriggers
from website.util import permissions as osf_permissions

# Required permission to perform each action. `None` means no permissions required.
TRIGGER_PERMISSIONS = {
    DefaultTriggers.SUBMIT.value: None,
    DefaultTriggers.ACCEPT.value: 'accept_submissions',
    DefaultTriggers.REJECT.value: 'reject_submissions',
    DefaultTriggers.EDIT_COMMENT.value: 'edit_review_comments',
}


class ReviewActionPermission(drf_permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        if auth.user is None:
            return False

        target = None
        provider = None
        if isinstance(obj, ReviewAction):
            target = obj.target
            provider = target.provider
        elif isinstance(obj, ReviewableMixin):
            target = obj
            provider = target.provider
        elif isinstance(obj, ReviewProviderMixin):
            provider = obj
        else:
            raise ValueError('Not a reviews-related model: {}'.format(obj))

        serializer = view.get_serializer()

        if request.method in drf_permissions.SAFE_METHODS:
            # Moderators and node contributors can view actions
            is_node_contributor = target is not None and target.node.has_permission(auth.user, osf_permissions.READ)
            return is_node_contributor or auth.user.has_perm('view_actions', provider)
        else:
            # Moderators and node admins can trigger state changes.
            is_node_admin = target is not None and target.node.has_permission(auth.user, osf_permissions.ADMIN)
            if not (is_node_admin or auth.user.has_perm('view_submissions', provider)):
                return False

            # User can trigger state changes on this reviewable, but can they use this trigger in particular?
            serializer = view.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            trigger = serializer.validated_data.get('trigger')
            permission = TRIGGER_PERMISSIONS[trigger]
            return permission is None or request.user.has_perm(permission, target.provider)
