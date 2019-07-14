from rest_framework import permissions

from api.base.utils import get_user_auth, assert_resource_type
from osf.models import (
    DraftRegistration,
    DraftRegistrationContributor,
    OSFUser,
)
from osf.utils import permissions as osf_permissions


class IsContributorOrAdminContributor(permissions.BasePermission):
    """
    Need to be a contributor on the draft registration to view, otherwise,
    you need to be an admin contributor to make edits
    """

    acceptable_models = (DraftRegistration,)

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, dict):
            obj = obj.get('self', None)
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.can_view(auth)
        else:
            return obj.is_admin_contributor(auth.user)


class DraftContributorDetailPermissions(IsContributorOrAdminContributor):

    acceptable_models = (DraftRegistration, OSFUser, DraftRegistrationContributor,)

    def load_resource(self, context, view):
        return DraftRegistration.load(context['draft_id'])

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        context = request.parser_context['kwargs']
        preprint = self.load_resource(context, view)
        auth = get_user_auth(request)
        user = OSFUser.load(context['user_id'])

        if request.method in permissions.SAFE_METHODS:
            return super(DraftContributorDetailPermissions, self).has_object_permission(request, view, preprint)
        elif request.method == 'DELETE':
            return preprint.has_permission(auth.user, osf_permissions.ADMIN) or auth.user == user
        else:
            return preprint.has_permission(auth.user, osf_permissions.ADMIN)
