from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied

from api.base.exceptions import Gone
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.comments.permissions import (
    CommentDetailPermissions,
    CommentReportsPermissions
)
from api.comments.serializers import (
    CommentSerializer,
    NodeCommentDetailSerializer,
    RegistrationCommentDetailSerializer,
    CommentReportSerializer,
    CommentReportDetailSerializer,
    CommentReport
)
from framework.auth.core import Auth
from framework.auth.oauth_scopes import CoreScopes
from framework.exceptions import PermissionsError
from osf.models import AbstractNode, Comment, BaseFileNode
from addons.wiki.models import NodeWikiPage


class CommentMixin(object):
    """Mixin with convenience methods for retrieving the current comment  based on the
    current URL. By default, fetches the comment based on the comment_id kwarg.
    """

    serializer_class = CommentSerializer
    comment_lookup_url_kwarg = 'comment_id'

    def get_comment(self, check_permissions=True):
        pk = self.kwargs[self.comment_lookup_url_kwarg]
        comment = get_object_or_404(Comment, guids___id=pk, root_target__isnull=False)

        # Deleted root targets still appear as tuples in the database and are included in
        # the above query, requiring an additional check
        if comment.root_target.referent.is_deleted:
            comment.root_target = None
            comment.save()

        if comment.root_target is None:
            raise NotFound

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, comment)
        return comment


class CommentDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, CommentMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/comments_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CommentDetailPermissions,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_COMMENTS_READ]
    required_write_scopes = [CoreScopes.NODE_COMMENTS_WRITE]

    serializer_class = NodeCommentDetailSerializer
    view_category = 'comments'
    view_name = 'comment-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        comment = self.get_comment()
        comment_node = None

        if isinstance(comment.target.referent, AbstractNode):
            comment_node = comment.target.referent
        elif isinstance(comment.target.referent, (NodeWikiPage,
                                                  BaseFileNode)):
            comment_node = comment.target.referent.node

        if comment_node and comment_node.is_registration:
            self.serializer_class = RegistrationCommentDetailSerializer

        return comment

    def perform_destroy(self, instance):
        auth = Auth(self.request.user)
        if instance.is_deleted:
            raise ValidationError('Comment already deleted.')
        else:
            try:
                instance.delete(auth, save=True)
            except PermissionsError:
                raise PermissionDenied('Not authorized to delete this comment.')


class CommentReportsList(JSONAPIBaseView, generics.ListCreateAPIView, CommentMixin):
    """List of reports made for a comment. *Writeable*.

    Paginated list of reports for a comment. Each resource contains the full representation of the
    report, meaning additional requests to an individual comment's report detail view are not necessary.

    ###Permissions

    The comment reports endpoint can only be viewed by users with permission to comment on the node. Users
    are only shown comment reports that they have made.

    ##Attributes

    OSF comment report entities have the "comment_reports" `type`.

        name           type               description
        =====================================================================================
        category        string            the type of spam, must be one of the allowed values
        message         string            description of why the comment was reported

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "comment_reports",      # required
                           "attributes": {
                             "category":       {category}, # mandatory
                             "message":        {text},     # optional
                           }
                         }
                       }
        Success:       201 CREATED + comment report representation

    To create a report for this comment, issue a POST request against this endpoint. The `category` field is mandatory,
    and must be one of the following: "spam", "hate" or "violence" . The `message` field is optional. If the comment
    report creation is successful the API will return a 201 response with the representation of the new comment report
    in the body. For the new comment report's canonical URL, see the `/links/self` field of the response.

    ##Query Params

    *None*.

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        CommentReportsPermissions,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.COMMENT_REPORTS_READ]
    required_write_scopes = [CoreScopes.COMMENT_REPORTS_WRITE]

    serializer_class = CommentReportSerializer

    view_category = 'comments'
    view_name = 'comment-reports'

    ordering = ('-modified',)

    def get_queryset(self):
        user_id = self.request.user._id
        comment = self.get_comment()
        reports = comment.reports
        serialized_reports = []
        if user_id in reports:
            report = CommentReport(user_id, reports[user_id]['category'], reports[user_id]['text'])
            serialized_reports.append(report)
        return serialized_reports


class CommentReportDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, CommentMixin):
    """Details about a specific comment report. *Writeable*.

    ###Permissions

    A comment report detail can only be viewed, edited and removed by the user who created the report.

    ##Attributes

    OSF comment report entities have the "comment_reports" `type`.

        name           type               description
        =====================================================================================
        category        string            the type of spam, must be one of the allowed values
        message         string            description of why the comment was reported

    ##Links

        self:  the canonical api endpoint of this comment report

    ##Actions

    ###Update

        Method:        PUT / PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "comment_reports",   # required
                           "id":   {user_id},           # required
                           "attributes": {
                             "category":       {category},      # mandatory
                             "message":         {text},         # optional
                           }
                         }
                       }
        Success:       200 OK + comment report representation

    To update a report for this comment, issue a PUT/PATCH request against this endpoint. The `category` field is
    mandatory for a PUT request and must be one of the following: "spam", "hate" or "violence". The `message` field
    is optional. Non-string values will be accepted and stringified, but we make no promises about the stringification
    output. So don't do that.

    ###Delete
        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Success:       204 + No content

    To delete a comment report, issue a DELETE request against `/links/self`.  A successful delete will return a
    204 No Content response.

    ##Query Params

    *None*.

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        CommentReportsPermissions,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.COMMENT_REPORTS_READ]
    required_write_scopes = [CoreScopes.COMMENT_REPORTS_WRITE]

    serializer_class = CommentReportDetailSerializer
    view_category = 'comments'
    view_name = 'report-detail'

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        comment = self.get_comment()
        reports = comment.reports
        user_id = self.request.user._id
        reporter_id = self.kwargs['user_id']

        if reporter_id != user_id:
            raise PermissionDenied('Not authorized to comment on this project.')

        if reporter_id in reports:
            return CommentReport(user_id, reports[user_id]['category'], reports[user_id]['text'])
        else:
            raise Gone(detail='The requested comment report is no longer available.')

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        user = self.request.user
        comment = self.get_comment()
        try:
            comment.retract_report(user, save=True)
        except ValueError as error:
            raise ValidationError(error.message)
