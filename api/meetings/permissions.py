from rest_framework import permissions

from api.base.utils import assert_resource_type
from osf.models import AbstractNode


class IsPublic(permissions.BasePermission):
    """
    Only returning public nodes as meeting submissions.
    """

    acceptable_models = (AbstractNode,)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        return obj.is_public
