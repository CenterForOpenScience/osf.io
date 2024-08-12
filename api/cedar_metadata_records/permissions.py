import logging

from rest_framework import permissions

from api.base.utils import get_user_auth

from osf.models import BaseFileNode, CedarMetadataRecord, Node, Registration

logger = logging.getLogger(__name__)


class CedarMetadataRecordPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(
            obj,
            CedarMetadataRecord,
        ), "obj must be a CedarMetadataRecord"
        auth = get_user_auth(request)

        permission_source = obj.guid.referent
        if isinstance(permission_source, BaseFileNode):
            permission_source = permission_source.target
        elif not isinstance(permission_source, (Node, Registration)):
            return False

        if request.method in permissions.SAFE_METHODS:
            if not obj.is_published:
                return permission_source.can_edit(auth)
            return permission_source.is_public or permission_source.can_view(
                auth,
            )
        return permission_source.can_edit(auth)
