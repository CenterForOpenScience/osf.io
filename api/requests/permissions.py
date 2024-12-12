from rest_framework import permissions as drf_permissions

from api.base.utils import get_user_auth
from osf.models import (
    Node,
    NodeRequestAction,
    PreprintRequestAction,
    Preprint,
    Institution,
)
from osf.models.mixins import NodeRequestableMixin, PreprintRequestableMixin
from osf.utils.workflows import DefaultTriggers, NodeRequestTypes
from osf.utils import permissions as osf_permissions


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
        elif isinstance(obj, NodeRequestableMixin):
            target = obj
            node = obj.target
            # Creating a Request is "submitting"
            trigger = request.data.get('trigger', DefaultTriggers.SUBMIT.value if request.method not in drf_permissions.SAFE_METHODS else None)
        elif isinstance(obj, Node):
            node = obj
            trigger = DefaultTriggers.SUBMIT.value if request.method not in drf_permissions.SAFE_METHODS else None
        else:
            raise ValueError(f'Not a request-related model: {obj}')

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


class InstitutionalAdminRequestTypePermission(drf_permissions.BasePermission):
    """
    Permission class for handling object permissions related to Node requests and actions.
    """

    def has_permission(self, request, view):
        # Skip if not institutional_request request_type
        request_type = request.data.get('request_type')
        if request_type != NodeRequestTypes.INSTITUTIONAL_REQUEST.value:
            return True

        auth = get_user_auth(request)
        if not auth.user:
            return False

        institution_id = request.data.get('institution')
        if not institution_id:
            return False

        try:
            institution = Institution.objects.get(_id=institution_id)
        except Institution.DoesNotExist:
            return False

        return auth.user.is_institutional_admin(institution)


class PreprintRequestPermission(drf_permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        if auth.user is None:
            return False

        target = None
        if isinstance(obj, PreprintRequestAction):
            target = obj.target
            preprint = obj.target.target
            trigger = request.data.get('trigger', None)
        elif isinstance(obj, PreprintRequestableMixin):
            target = obj
            preprint = obj.target
            # Creating a Request is "submitting"
            trigger = request.data.get('trigger', DefaultTriggers.SUBMIT.value if request.method not in drf_permissions.SAFE_METHODS else None)
        elif isinstance(obj, Preprint):
            preprint = obj
            trigger = DefaultTriggers.SUBMIT.value if request.method not in drf_permissions.SAFE_METHODS else None
        else:
            raise ValueError(f'Not a request-related model: {obj}')

        is_requester = target is not None and target.creator == auth.user or trigger == DefaultTriggers.SUBMIT.value
        is_preprint_admin = preprint.has_permission(auth.user, osf_permissions.ADMIN)
        is_moderator = auth.user.has_perm('withdraw_submissions', preprint.provider)
        has_view_permission = is_requester or is_preprint_admin or is_moderator

        if request.method in drf_permissions.SAFE_METHODS:
            # Requesters, moderators, and preprint admins can view actions
            return has_view_permission
        else:
            if not has_view_permission:
                return False

            if trigger in [DefaultTriggers.ACCEPT.value, DefaultTriggers.REJECT.value]:
                # Only moderators can approve or reject requests
                return is_moderator
            if trigger in [DefaultTriggers.EDIT_COMMENT.value, DefaultTriggers.SUBMIT.value]:
                # Requesters may edit their comment or submit their request
                return is_requester
            return False
