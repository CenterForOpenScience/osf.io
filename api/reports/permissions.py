# -*- coding: utf-8 -*-
from rest_framework import permissions

from api.base.utils import get_user_auth
from api.reports.serializers import CommentReport
from website.models import Comment


class CommentReportsPermissions(permissions.BasePermission):
    """Permissions for comment reports. Only users who have permission to comment on the project
       can access the comment reports endpoint."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Comment, CommentReport)), 'obj must be a Comment or Comment Report, got {}'.format(obj)
        auth = get_user_auth(request)
        if isinstance(obj, Comment):
            node = obj.node
        elif isinstance(obj, CommentReport):
            comment = view.get_comment()
            node = comment.node
        return node.can_comment(auth)
