from rest_framework import generics, renderers, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from rest_framework.views import Response

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from api.base import permissions as base_permissions
from api.base.exceptions import Gone
from api.base.views import JSONAPIBaseView

from api.wikis.permissions import ContributorOrPublic
from api.wikis.serializers import WikiSerializer, WikiDetailSerializer
from framework.auth.oauth_scopes import CoreScopes
from website.addons.wiki.model import NodeWikiPage


class WikiRenderer(renderers.BaseRenderer):

    media_type = 'text/markdown'
    format = '.txt'

    def render(self, data, media_type=None,renderer_context=None):
        return data.encode(self.charset)

class WikiMixin(object):
    """Mixin with convenience methods for retrieving the wiki page based on the
    URL. By default, fetches the wiki page based on the wiki_id kwarg.
    """

    serializer_class = WikiSerializer
    wiki_lookup_url_kwarg = 'wiki_id'

    def get_wiki(self, check_permissions=True):
        pk = self.kwargs[self.wiki_lookup_url_kwarg]
        try:
            wiki = NodeWikiPage.find_one(Q('_id', 'eq', pk))
        except NoResultsFound:
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

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic
    )

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = WikiDetailSerializer
    view_category = 'wikis'
    view_name = 'wiki-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_wiki()


class WikiContent(JSONAPIBaseView, WikiMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic
    )

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    renderer_classes = (WikiRenderer, )
    view_category = 'wikis'
    view_name = 'wiki-content'

    def get_serializer_class(self):
        return None

    def get(self, request, **kwargs):
        wiki = self.get_wiki()
        return Response(wiki.content)
