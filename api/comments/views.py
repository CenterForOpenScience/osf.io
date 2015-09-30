from modularodm import Q
from modularodm.exceptions import NoResultsFound
from rest_framework import generics
from rest_framework.exceptions import NotFound
from api.comments.serializers import CommentSerializer, CommentDetailSerializer
from website.project.model import Comment


class CommentMixin(object):
    """Mixin with convenience methods for retrieving the current comment  based on the
    current URL. By default, fetches the comment based on the comment_id kwarg.
    """

    serializer_class = CommentSerializer
    comment_lookup_url_kwarg = 'comment_id'

    def get_comment(self, check_permissions=True):
        pk = self.kwargs[self.comment_lookup_url_kwarg]
        query = Q('_id', 'eq', pk)
        try:
            comment = Comment.find_one(query)
        except NoResultsFound:
            raise NotFound

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, comment)
        return comment


class CommentDetail(generics.RetrieveUpdateAPIView, CommentMixin):
    """Details about a specific comment.
    """
    # permission classes
    # required scopes

    serializer_class = CommentDetailSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_comment()
