from rest_framework import permissions

from api.base.utils import get_user_auth
from api.comments.serializers import CommentReport
from osf.models import AbstractNode, Comment

class CanCommentOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (AbstractNode, Comment)), f'obj must be a Node or Comment, got {obj}'
        auth = get_user_auth(request)
        if isinstance(obj, Comment):
            node = obj.node
        elif isinstance(obj, AbstractNode):
            node = obj

        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        else:
            return node.can_comment(auth)


class CommentDetailPermissions(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Comment), f'obj must be a Comment, got {obj}'
        auth = get_user_auth(request)
        comment = obj
        node = obj.node

        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        else:
            return comment.user._id == auth.user._id and node.can_comment(auth)


class CommentReportsPermissions(permissions.BasePermission):
    """Permissions for comment reports. Only users who have permission to comment on the project
       can access the comment reports endpoint."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Comment, CommentReport)), f'obj must be a Comment or Comment Report, got {obj}'
        auth = get_user_auth(request)
        if isinstance(obj, Comment):
            node = obj.node
        elif isinstance(obj, CommentReport):
            comment = view.get_comment()
            node = comment.node
        return node.can_comment(auth)
