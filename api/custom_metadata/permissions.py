from rest_framework import permissions

from api.base.utils import get_user_auth
from osf.models import GuidMetadataRecord, BaseFileNode


class CustomMetadataPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, GuidMetadataRecord)

        resource = obj.guid.referent
        if isinstance(resource, BaseFileNode):
            resource = resource.target
        auth = get_user_auth(request)

        print(resource.can_view(auth), obj, view)

        if request.method in permissions.SAFE_METHODS:
            return resource.is_public or resource.can_view(auth)
        else:
            return resource.can_edit(auth)
