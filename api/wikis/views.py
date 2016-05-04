from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from api.base import permissions as base_permissions
from api.base.exceptions import Gone
from api.base.views import JSONAPIBaseView

from api.wikis.serializers import WikiSerializer, WikiDetailSerializer
from framework.auth.oauth_scopes import CoreScopes
from website.addons.wiki.model import NodeWikiPage


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

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, wiki)
        return wiki


class WikiDetail(JSONAPIBaseView, generics.RetrieveAPIView, WikiMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = WikiDetailSerializer
    view_category = 'wikis'
    view_name = 'wiki-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_wiki()
