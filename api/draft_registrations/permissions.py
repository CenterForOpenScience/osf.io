from rest_framework import permissions

from api.base.utils import get_user_auth, assert_resource_type
from osf.models import (
    Node,
    DraftRegistration,
    AbstractNode,
    DraftRegistrationContributor,
    OSFUser,
)
from api.nodes.permissions import ContributorDetailPermissions

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

        if isinstance(obj, DraftRegistration) and isinstance(obj.branched_from, Node):
            obj = obj.branched_from

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

        if isinstance(obj, DraftRegistration) and isinstance(obj.branched_from, Node):
            obj = obj.branched_from

        if request.method in permissions.SAFE_METHODS:
            return obj.is_contributor(auth.user)
        else:
            return obj.is_admin_contributor(auth.user)

class DraftContributorDetailPermissions(ContributorDetailPermissions):

    acceptable_models = (DraftRegistration, OSFUser, DraftRegistrationContributor,)

    def load_resource(self, context, view):
        return DraftRegistration.load(context['draft_id'])
