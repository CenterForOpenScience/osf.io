# -*- coding: utf-8 -*-
from rest_framework import permissions

from website.models import Node, Pointer, User, Comment
from website.util import permissions as osf_permissions

from api.base.utils import get_user_auth


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, Pointer)), 'obj must be a Node or Pointer, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            return obj.can_edit(auth)


class AdminOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, User)), 'obj must be a Node or User, got {}'.format(obj)
        auth = get_user_auth(request)
        node = Node.load(request.parser_context['kwargs'][view.node_lookup_url_kwarg])
        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        else:
            return node.has_permission(auth.user, osf_permissions.ADMIN)


class ContributorDetailPermissions(permissions.BasePermission):
    """Permissions for contributor detail page."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, User)), 'obj must be User or Node, got {}'.format(obj)
        auth = get_user_auth(request)
        context = request.parser_context['kwargs']
        node = Node.load(context[view.node_lookup_url_kwarg])
        user = User.load(context['user_id'])
        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        elif request.method == 'DELETE':
            return node.has_permission(auth.user, osf_permissions.ADMIN) or auth.user == user
        else:
            return node.has_permission(auth.user, osf_permissions.ADMIN)


class ContributorOrPublicForPointers(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, Pointer)), 'obj must be a Node or Pointer, got {}'.format(obj)
        auth = get_user_auth(request)
        parent_node = Node.load(request.parser_context['kwargs']['node_id'])
        pointer_node = Pointer.load(request.parser_context['kwargs']['node_link_id']).node
        if request.method in permissions.SAFE_METHODS:
            has_parent_auth = parent_node.can_view(auth)
            has_pointer_auth = pointer_node.can_view(auth)
            public = obj.is_public
            has_auth = public or (has_parent_auth and has_pointer_auth)
            return has_auth
        else:
            has_auth = parent_node.can_edit(auth)
            return has_auth


class CanCommentOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, Comment)), 'obj must be a Node or Comment, got {}'.format(obj)
        auth = get_user_auth(request)
        if isinstance(obj, Comment):
            node = obj.node
        elif isinstance(obj, Node):
            node = obj

        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        else:
            return node.can_comment(auth)


class CommentDetailPermissions(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Comment), 'obj must be a Comment, got {}'.format(obj)
        auth = get_user_auth(request)
        comment = obj
        node = obj.node
        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        else:
            return comment.user._id == auth.user._id


class CommentReportsPermissions(permissions.BasePermission):
    """Permissions for comment reports. Only users who have permission to comment on the project
       can access the comment reports endpoint."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Comment), 'obj must be a Comment, got {}'.format(obj)
        auth = get_user_auth(request)
        node = obj.node
        return node.can_comment(auth)


class ReadOnlyIfRegistration(permissions.BasePermission):
    """Makes PUT and POST forbidden for registrations."""

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, Node):
            obj = Node.load(request.parser_context['kwargs'][view.node_lookup_url_kwarg])
        assert isinstance(obj, Node), 'obj must be a Node'
        if obj.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True
