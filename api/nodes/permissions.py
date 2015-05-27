from website.models import Node, Pointer
from rest_framework import permissions

from framework.auth import Auth

def get_user_auth(request):
    user = request.user
    if user.is_anonymous():
        auth = Auth(None)
    else:
        auth = Auth(user)
    return auth

class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Node), 'obj must be a Node, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            return obj.can_edit(auth)


class ContributorOrPublicForPointers(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Node), 'obj must be a Node, got {}'.format(obj)
        auth = get_user_auth(request)
        parent_node = Node.load(request.parser_context['kwargs']['pk'])
        pointer_node = Pointer.load(request.parser_context['kwargs']['pointer_id']).node
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or (parent_node.can_view(auth) and pointer_node.can_view(auth))
        else:
            return parent_node.can_edit(auth) and pointer_node.can_edit(auth)


class ReadOnlyIfRegistration(permissions.BasePermission):
    """Makes PUT and POST forbidden for registrations."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Node), 'obj must be a Node'
        if obj.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True
