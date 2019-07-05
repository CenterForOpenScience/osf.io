from rest_framework import permissions

from api.base.utils import assert_resource_type, get_user_auth
from osf.utils.permissions import MANAGE
from osf.models import OSFGroup, OSFUser


class IsGroupManager(permissions.BasePermission):

    acceptable_models = (OSFGroup,)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)

        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return auth.user and obj.has_permission(auth.user, MANAGE)


class GroupMemberManagement(permissions.BasePermission):

    acceptable_models = (OSFGroup, OSFUser, )

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, OSFGroup):
            obj = OSFGroup.load(request.parser_context['kwargs']['group_id'])
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return True
        elif request.method == 'DELETE':
            user = OSFUser.load(request.parser_context['kwargs']['user_id'])
            # You must have manage permissions on the OSFGroup to remove a member,
            # unless you are removing yourself
            return obj.has_permission(auth.user, MANAGE) or auth.user == user
        else:
            return auth.user and obj.has_permission(auth.user, MANAGE)
