from modularodm import Q
from modularodm.exceptions import NoResultsFound
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied
from api.comments.serializers import (
    CommentSerializer,
    CommentDetailSerializer,
    CommentReportsSerializer,
    CommentReportDetailSerializer,
    CommentReport
)
from api.base.exceptions import Gone
from api.base import permissions as base_permissions
from api.nodes.permissions import ContributorOrPublicForComments
from framework.auth.oauth_scopes import CoreScopes
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


class CommentRepliesList(generics.ListCreateAPIView, CommentMixin):
    """Replies to a comment.

    By default, a GET will return both deleted and not deleted replies. Comment replies may be
    filtered by their `deleted` field.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublicForComments,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_COMMENTS_READ]
    required_write_scopes = [CoreScopes.NODE_COMMENTS_WRITE]

    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.find(Q('target', 'eq', self.get_comment()))

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        target = self.get_comment()
        serializer.validated_data['user'] = self.request.user
        serializer.validated_data['target'] = target
        serializer.validated_data['node'] = target.node
        serializer.save()


class CommentDetail(generics.RetrieveUpdateAPIView, CommentMixin):
    """Details about a specific comment."""
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublicForComments,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_COMMENTS_READ]
    required_write_scopes = [CoreScopes.NODE_COMMENTS_WRITE]

    serializer_class = CommentDetailSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_comment()


class CommentReportsList(generics.ListCreateAPIView, CommentMixin):
    """List of reports made for a comment."""
    permission_classes = (
        drf_permissions.IsAuthenticated,
        ContributorOrPublicForComments,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.COMMENT_REPORTS_READ]
    required_write_scopes = [CoreScopes.COMMENT_REPORTS_WRITE]

    serializer_class = CommentReportsSerializer

    def get_queryset(self):
        user_id = self.request.user._id
        comment = self.get_comment()
        reports = comment.reports
        serialized_reports = []
        if user_id in reports:
            report = CommentReport(user_id, reports[user_id]['category'], reports[user_id]['text'])
            serialized_reports.append(report)
        return serialized_reports


class CommentReportDetail(generics.RetrieveUpdateDestroyAPIView, CommentMixin):
    """Details about a specific comment report."""
    permission_classes = (
        drf_permissions.IsAuthenticated,
        ContributorOrPublicForComments,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.COMMENT_REPORTS_READ]
    required_write_scopes = [CoreScopes.COMMENT_REPORTS_WRITE]

    serializer_class = CommentReportDetailSerializer

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        comment = self.get_comment()
        reports = comment.reports
        user_id = self.request.user._id
        reporter_id = self.kwargs['user_id']

        if reporter_id != user_id:
            raise PermissionDenied("Not authorized to comment on this project.")

        if reporter_id in reports:
            return CommentReport(user_id, reports[user_id]['category'], reports[user_id]['text'])
        else:
            raise Gone(detail='The requested comment report is no longer available.')

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        user = self.request.user
        comment = self.get_comment()
        try:
            comment.unreport_abuse(user, save=True)
        except ValueError as error:
            raise ValidationError(error.message)
