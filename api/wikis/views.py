from django.core import exceptions as django_exceptions
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound, ValidationError, MethodNotAllowed
from rest_framework.views import Response

from framework.auth.oauth_scopes import CoreScopes


from api.base import permissions as base_permissions
from api.base.exceptions import Gone
from api.base.utils import get_user_auth
from api.base.views import JSONAPIBaseView
from api.base.renderers import PlainTextRenderer
from api.wikis.permissions import (
    ContributorOrPublic,
    ExcludeWithdrawals,
    ContributorOrPublicWikiVersion,
    ExcludeWithdrawalsWikiVersion,
)
from api.wikis.serializers import (
    WikiSerializer,
    WikiVersionSerializer,
    NodeWikiDetailSerializer,
    RegistrationWikiDetailSerializer,
)
from addons.wiki.models import WikiPage

from website.files.exceptions import VersionNotFoundError


class WikiMixin(object):
    """Mixin with convenience methods for retrieving the wiki page based on the
    URL. By default, fetches the wiki page based on the wiki_id kwarg.
    """

    serializer_class = WikiSerializer
    wiki_lookup_url_kwarg = 'wiki_id'

    def get_wiki(self, check_permissions=True):
        pk = self.kwargs[self.wiki_lookup_url_kwarg]
        wiki = WikiPage.load(pk)
        if not wiki:
            raise NotFound

        if wiki.node.addons_wiki_node_settings.deleted:
            raise NotFound(detail='The wiki for this node has been disabled.')

        if wiki.deleted:
            raise Gone

        if wiki.node.is_registration and self.request.method not in drf_permissions.SAFE_METHODS:
            raise MethodNotAllowed(method=self.request.method)

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, wiki)
        return wiki

    def get_wiki_version(self, check_permissions=True):
        version_lookup_url_kwarg = 'version_id'

        version = self.kwargs[version_lookup_url_kwarg]
        wiki_page = self.get_wiki(check_permissions=False)
        try:
            wiki_version = wiki_page.get_version(version)
            if check_permissions:
                self.check_object_permissions(self.request, wiki_version)
            return wiki_version
        except VersionNotFoundError:
            raise NotFound


class WikiDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, WikiMixin):
    """Details about a specific wiki.

    ###Permissions

    Wiki pages on public nodes are given read-only access to everyone. Wiki pages on private nodes are only visible to
    contributors and administrators on the parent node.

    Note that if an anonymous view_only key is being used, the user relationship will not be exposed.

    ##Attributes

    OSF wiki entities have the "wikis" `type`.

         name                        type                   description
         ======================================================================================================
         name                        string             name of the wiki page
         path                        string             the path of the wiki page
         materialized_path           string             the path of the wiki page
         date_modified               iso8601 timestamp  timestamp when the wiki was last updated
         content_type                string             MIME-type
         current_user_can_comment    boolean            Whether the current user is allowed to post comments
         extra                       object
         version                     integer            version number of the wiki


    ##Relationships

    ###User

    The user who created the wiki.

    ###Node

    The project that the wiki page belongs to.

    ###Comments

    The comments created on the wiki page.

    ##Links

        self:  the canonical api endpoint of this wiki
        info: the canonical api endpoint of this wiki
        download: the link to retrive the contents of the wiki page

    ##Query Params

    *None*.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
        ExcludeWithdrawals
    )

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.WIKI_BASE_WRITE]

    serializer_class = NodeWikiDetailSerializer
    view_category = 'wikis'
    view_name = 'wiki-detail'

    def get_serializer_class(self):
        if self.get_wiki().node.is_registration:
            return RegistrationWikiDetailSerializer
        return NodeWikiDetailSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_wiki()

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        wiki_page = self.get_object()
        try:
            wiki_page.delete(auth)
        except django_exceptions.ValidationError as err:
            raise ValidationError(err.message)


class WikiContent(JSONAPIBaseView, generics.RetrieveAPIView, WikiMixin):
    """ View for rendering wiki page content."""

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
        ExcludeWithdrawals
    )

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    renderer_classes = (PlainTextRenderer, )
    view_category = 'wikis'
    view_name = 'wiki-content'

    def get_serializer_class(self):
        return None

    def get(self, request, **kwargs):
        wiki = self.get_wiki()
        return Response(wiki.get_version().content)


class WikiVersions(JSONAPIBaseView, generics.ListCreateAPIView, WikiMixin):
    """
    View for rendering all versions of a particular WikiPage
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
        ExcludeWithdrawals
    )
    view_category = 'wikis'
    view_name = 'wiki-versions'
    serializer_class = WikiVersionSerializer

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.WIKI_BASE_WRITE]

    def get_queryset(self):
        return self.get_wiki().get_versions()

    def perform_create(self, serializer):
        serializer.save(content=self.request.data.get('content'))


class WikiVersionDetail(JSONAPIBaseView, generics.RetrieveAPIView, WikiMixin):
    """
    Details about a specific wiki version. *Read-only*.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublicWikiVersion,
        ExcludeWithdrawalsWikiVersion
    )

    serializer_class = WikiVersionSerializer

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'wikis'
    view_name = 'wiki-version-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_wiki_version()


class WikiVersionContent(JSONAPIBaseView, generics.RetrieveAPIView, WikiMixin):
    """
    View for rendering wiki content for a specific version.
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublicWikiVersion,
        ExcludeWithdrawalsWikiVersion
    )

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    renderer_classes = (PlainTextRenderer, )
    view_category = 'wikis'
    view_name = 'wiki-version-content'

    def get_serializer_class(self):
        return None

    def get(self, request, **kwargs):
        wiki_version = self.get_wiki_version()
        return Response(wiki_version.content)
