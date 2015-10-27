from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from api.base.exceptions import Gone
from api.base import permissions as base_permissions
from api.comments.serializers import (
    CommentSerializer,
    CommentDetailSerializer,
    CommentReportsSerializer,
    CommentReportDetailSerializer,
    CommentReport
)
from api.nodes.permissions import (
    CanCommentOrPublic,
    CommentDetailPermissions,
    CommentReportsPermissions)
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
        try:
            comment = Comment.find_one(Q('_id', 'eq', pk))
        except NoResultsFound:
            raise NotFound

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, comment)
        return comment


class CommentRepliesList(generics.ListCreateAPIView, CommentMixin):
    """List of replies to a comment. *Writeable*.

    Paginated list of comment replies ordered by their `date_created.` Each resource contains the full representation
    of the comment, meaning additional requests to an individual comment's detail view are not necessary.

    ###Permissions

    Comments on public nodes are given read-only access to everyone. If the node comment-level is "private",
    only contributors have permission to comment. If the comment-level is "public" any logged-in OSF user can comment.
    Comments on private nodes are only visible to contributors and administrators on the parent node.

    ##Attributes

    OSF comment reply entities have the "comments" `type`.

        name           type               description
        ---------------------------------------------------------------------------------
        content        string             content of the comment
        date_created   iso8601 timestamp  timestamp that the comment was created
        date_modified  iso8601 timestamp  timestamp when the comment was last updated
        modified       boolean            has this comment been edited?
        deleted        boolean            is this comment deleted?

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    ###Create

        Method:        POST
        URL:           links.self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "comments",   # required
                           "attributes": {
                             "content":       {content},        # mandatory
                             "deleted":       {is_deleted},     # optional
                           }
                         }
                       }
        Success:       201 CREATED + comment representation

    To create a comment reply, issue a POST request against this endpoint.  The `content` field is mandatory. The
    `deleted` field is optional and defaults to `False`. If the comment reply creation is successful the API will return
    a 201 response with the representation of the new comment reply in the body. For the new comment reply's canonical
    URL, see the `links.self` field of the response.

    ##Query Params

    + `filter[deleted]=True|False` -- filter comment replies based on whether or not they are deleted.

    The list of comment replies includes deleted comments by default. The `deleted` field is a boolean and can be
    filtered using truthy values, such as `true`, `false`, `0`, or `1`. Note that quoting `true` or `false` in
    the query will cause the match to fail regardless.

    #This Request/Response
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CanCommentOrPublic,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_COMMENTS_READ]
    required_write_scopes = [CoreScopes.NODE_COMMENTS_WRITE]

    serializer_class = CommentSerializer

    ordering = ('-date_created', )  # default ordering

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
    """Details about a specific comment. *Writeable*.

    ###Permissions

    Comments on public nodes are given read-only access to everyone. Comments on private nodes are only visible
    to contributors and administrators on the parent node. Only the user who created the comment has permissions
    to edit and delete the comment.

    ##Attributes

    OSF comment entities have the "comments" `type`.

        name           type               description
        ---------------------------------------------------------------------------------
        content        string             content of the comment
        date_created   iso8601 timestamp  timestamp that the comment was created
        date_modified  iso8601 timestamp  timestamp when the comment was last updated
        modified       boolean            has this comment been edited?
        deleted        boolean            is this comment deleted?

    ##Relationships

    ###User

    The user who created the comment.

    ###Node

    The project associated with this comment.

    ###Target

    The "parent" of the comment. If the comment was made on a node, the target is the node. If the comment
    is a reply, its target is the comment it was in reply to.

    ###Replies
    List of replies to this comment. New replies can be created through this endpoint.

    ###Reports
    List of spam reports for this comment. Only users with permissions to create comments can
    access this endpoint, and users can only see reports that they have created.

    ##Links

        self:  the canonical api endpoint of this node

    ##Actions

    ###Update

        Method:        PUT / PATCH
        URL:           links.self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "comments",   # required
                           "id":   {comment_id}, # required
                           "attributes": {
                             "content":       {content},        # mandatory
                             "deleted":       {is_deleted},     # mandatory
                           }
                         }
                       }
        Success:       200 OK + comment representation

    To update a comment, issue either a PUT or a PATCH request against the `links.self` URL.  The `content`
    and 'deleted' fields are mandatory if you PUT and optional if you PATCH. Non-string values will be accepted and
    stringified, but we make no promises about the stringification output.  So don't do that.

    To delete a comment, issue a PATCH request against the `links.self` URL, with `is_deleted: True`:

    To undelete a comment, issue a PATCH request against the `links.self` URL, with `is_deleted: False`.

    ##Query Params

    *None*.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CommentDetailPermissions,
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
        CommentReportsPermissions,
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
        CommentReportsPermissions,
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
