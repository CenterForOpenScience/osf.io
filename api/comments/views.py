from rest_framework import generics
from api.comments.serializers import CommentSerializer
from website.project.model import Comment
from modularodm import Q
from api.base.utils import get_object_or_error


class CommentMixin(object):
    """Mixin with convenience methods for retrieving the current comment  based on the
    current URL. By default, fetches the comment based on the comment_id kwarg.
    """

    serializer_class = CommentSerializer
    comment_lookup_url_kwarg = 'comment_id'

    def get_comment(self, check_permissions=True):
        comment = get_object_or_error(Comment, self.kwargs[self.comment_lookup_url_kwarg])

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, comment)
        return comment


class CommentDetail(generics.RetrieveUpdateAPIView, CommentMixin):
    """Details about a specific comment.
    """
    # permission classes
    # required scopes

    serializer_class = CommentSerializer

    def get_object(self):
        return self.get_comment()
