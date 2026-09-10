import waffle
from rest_framework import exceptions, permissions

from api.base.utils import get_user_auth
from osf import features
from osf.models import GuidMetadataRecord, BaseFileNode, Node


class CustomMetadataPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, GuidMetadataRecord)

        delegate_obj = obj.guid.referent
        if isinstance(delegate_obj, BaseFileNode):
            delegate_obj = delegate_obj.target
        auth = get_user_auth(request)

        if request.method in permissions.SAFE_METHODS:
            return delegate_obj.is_public or delegate_obj.can_view(auth)
        else:
            return delegate_obj.can_edit(auth)


class ItemMetadataEditingNotAllowed(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, GuidMetadataRecord)
        if request.method in permissions.SAFE_METHODS:
            return True
        delegate_obj = obj.guid.referent
        if isinstance(delegate_obj, Node) and waffle.flag_is_active(request, features.PROJECT_READ_ONLY):
            raise exceptions.MethodNotAllowed(
                request.method,
                detail='This action is no longer available. Contact support if you have any questions.',
            )
        return True
