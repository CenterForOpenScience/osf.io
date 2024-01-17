from rest_framework import permissions

from api.base.utils import get_user_auth

from osf.models import BaseFileNode, CedarMetadataRecord, Node, Registration


class CedarMetadataRecordPermission(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):

        assert isinstance(obj, CedarMetadataRecord), 'obj must be a CedarMetadataRecord'

        auth = get_user_auth(request)

        delegated_object = obj.guid.referent
        if isinstance(delegated_object, BaseFileNode):
            delegated_object = delegated_object.target
        elif not isinstance(delegated_object, Node) and not isinstance(delegated_object, Registration):
            return False

        if request.method in permissions.SAFE_METHODS:
            is_public = delegated_object.is_public and obj.is_published
            return is_public or delegated_object.can_view(auth)
        return delegated_object.can_edit(auth)
