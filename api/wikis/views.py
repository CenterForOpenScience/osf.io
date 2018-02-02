from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from rest_framework.views import Response

from api.base import permissions as base_permissions
from api.base.exceptions import Gone
from api.base.views import JSONAPIBaseView
from api.base.renderers import PlainTextRenderer
from api.wikis.permissions import ContributorOrPublic, ExcludeWithdrawals
from api.wikis.serializers import (
    WikiSerializer,
    NodeWikiDetailSerializer,
    RegistrationWikiDetailSerializer,
)

from framework.auth.oauth_scopes import CoreScopes
from addons.wiki.models import NodeWikiPage


class WikiMixin(object):
    """Mixin with convenience methods for retrieving the wiki page based on the
    URL. By default, fetches the wiki page based on the wiki_id kwarg.
    """

    serializer_class = WikiSerializer
    wiki_lookup_url_kwarg = 'wiki_id'

    def get_wiki(self, check_permissions=True):
        pk = self.kwargs[self.wiki_lookup_url_kwarg]
        wiki = NodeWikiPage.load(pk)
        if not wiki:
            raise NotFound

        if wiki.is_deleted:
            raise Gone

        # only show current wiki versions
        if not wiki.is_current:
            raise NotFound

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, wiki)
        return wiki


class WikiDetail(JSONAPIBaseView, generics.RetrieveAPIView, WikiMixin):

    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Wikis_wiki_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
        ExcludeWithdrawals
    )

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

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
        return Response(wiki.content)
