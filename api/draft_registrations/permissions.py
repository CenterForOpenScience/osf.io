from rest_framework import permissions

from api.base.utils import get_user_auth, assert_resource_type
from osf.models import (
    DraftRegistration,
    AbstractNode,
    DraftRegistrationContributor,
    OSFUser,
)
from osf.utils import permissions as osf_permissions
from website.project.metadata.utils import is_prereg_admin


class IsAdminContributor(permissions.BasePermission):
    """
    Use on API views where the requesting user needs to be an
    admin contributor to make changes.
    """
    acceptable_models = (DraftRegistration, AbstractNode)

    def has_object_permission(self, request, view, obj):
        # Unlike node.permissions::IsAdminContributor, DraftRegistration
        # permissions are not pulled off of the attached node
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.has_permission(auth.user, osf_permissions.ADMIN)
        else:
            return obj.is_admin_contributor(auth.user)


class IsAdminContributorOrReviewer(IsAdminContributor):
    """
    Prereg admins can update draft registrations.
    """
    acceptable_models = (AbstractNode, DraftRegistration,)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if request.method != 'DELETE' and is_prereg_admin(auth.user):
            return True
        return super(IsAdminContributorOrReviewer, self).has_object_permission(request, view, obj)


class IsContributor(permissions.BasePermission):

    acceptable_models = (DraftRegistration,)

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, dict):
            obj = obj.get('self', None)
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.can_view(auth)
        else:
            return obj.has_permission(auth.user, osf_permissions.ADMIN)


class DraftContributorDetailPermissions(IsContributor):

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
