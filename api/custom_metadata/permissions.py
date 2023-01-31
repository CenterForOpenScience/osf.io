from rest_framework import permissions

from api.base.utils import get_user_auth
from osf.models import GuidMetadataRecord, BaseFileNode


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
