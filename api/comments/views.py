from modularodm import Q
from modularodm.exceptions import NoResultsFound
from rest_framework import generics
from rest_framework.exceptions import NotFound, ValidationError
from api.comments.serializers import CommentSerializer, CommentDetailSerializer, CommentReportsSerializer, CommentReportDetailSerializer
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

    def serialize_comment_report(self, reports, user_id):
        user_dict = {}
        user_dict['_id'] = user_id
        user_dict['category'] = reports[user_id]['category']
        user_dict['message'] = reports[user_id]['text']
        return user_dict


class CommentDetail(generics.RetrieveUpdateAPIView, CommentMixin):
    """Details about a specific comment.
    """
    # permission classes
    # required scopes

    serializer_class = CommentDetailSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_comment()


class CommentReports(generics.ListCreateAPIView, CommentMixin):
    """Reporting a comment.
    """
    # permission classes
    # required scopes

    serializer_class = CommentReportsSerializer

    def get_queryset(self):
        comment = self.get_comment()
        reports = comment.reports
        serialized_reports = []

        for user_id in reports:
            report = self.serialize_comment_report(reports, user_id)
            serialized_reports.append(report)

        return serialized_reports


class CommentReportDetail(generics.RetrieveUpdateDestroyAPIView, CommentMixin):
    """Reporting a comment.
    """
    # permission classes
    # required scopes

    serializer_class = CommentReportDetailSerializer

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        comment = self.get_comment()
        reports = comment.reports
        user_id = self.kwargs['user_id']
        return self.serialize_comment_report(reports, user_id)

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        user = self.request.user
        comment = self.get_comment()
        try:
            comment.unreport_abuse(user, save=True)
        except ValueError as error:
            raise ValidationError(error.message)
