from rest_framework import permissions

from api.base.utils import get_user_auth, assert_resource_type
from osf.models import (
    DraftRegistration,
    AbstractNode,
    DraftRegistrationContributor,
    OSFUser,
)
from api.nodes.permissions import ContributorDetailPermissions
from osf.utils.permissions import READ, WRITE, ADMIN


class IsContributorOrAdminContributor(permissions.BasePermission):
    """
    Need to be a contributor on the branched from node to view.
    Need to have edit permissions on the branched from node to edit.
    """

    acceptable_models = (DraftRegistration, AbstractNode, )

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, dict):
            obj = obj.get('self', None)
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if not auth:
            return False

        if request.method in permissions.SAFE_METHODS:
            return obj.is_contributor(auth.user)
        else:
            return obj.can_edit(auth)

class IsAdminContributor(permissions.BasePermission):
    """
    Need to be a contributor on the branched from node to view.
    Need to be an admin contributor on the branched from node to make edits
    """

    acceptable_models = (DraftRegistration, AbstractNode, )

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, dict):
            obj = obj.get('self', None)
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if not auth.user:
            return False

        if request.method in permissions.SAFE_METHODS:
            return obj.is_contributor(auth.user)
        else:
            return obj.is_admin_contributor(auth.user)

class DraftContributorDetailPermissions(ContributorDetailPermissions):

    acceptable_models = (DraftRegistration, OSFUser, DraftRegistrationContributor,)

    def load_resource(self, context, view):
        return DraftRegistration.load(context['draft_id'])


class DraftRegistrationPermission(permissions.BasePermission):
    """
    Check permissions for draft and node, Admin can create (POST) or edit (PATCH, PUT) to a DraftRegistration, but write
    users can only edit them. Node permissions are inherited by the DraftRegistration when they are higher.
    """
    acceptable_models = (DraftRegistration, AbstractNode)

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        node_permission = False

        if request.method in permissions.SAFE_METHODS:
            if isinstance(obj, DraftRegistration):
                node_permission = obj.branched_from.has_permission(auth.user, READ)
            return obj.has_permission(auth.user, READ) or node_permission
        elif request.method == 'POST':  # Only Admin can create a draft registration
            if isinstance(obj, DraftRegistration):
                node_permission = obj.branched_from.has_permission(auth.user, ADMIN)
            return obj.has_permission(auth.user, ADMIN) or node_permission
        else:
            if isinstance(obj, DraftRegistration):
                node_permission = obj.branched_from.has_permission(auth.user, WRITE)
            return obj.has_permission(auth.user, WRITE) or node_permission
