from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from api.base.exceptions import Gone
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.wiki_versions.permissions import ContributorOrPublic, ExcludeWithdrawals
from api.wiki_versions.serializers import (
    WikiVersionSerializer,
)

from framework.auth.oauth_scopes import CoreScopes
from addons.wiki.models import WikiVersion


class WikiVersionMixin(object):
    """Mixin with convenience methods for retrieving the wiki version based on the
    URL. By default, fetches the wiki version based on the wiki_version_id kwarg.
    """
    wiki_lookup_url_kwarg = 'wiki_version_id'

    def get_wiki_version(self, check_permissions=True):
        pk = self.kwargs[self.wiki_lookup_url_kwarg]
        wiki = WikiVersion.load(pk)
        if not wiki:
            raise NotFound

        if wiki.wiki_page.is_deleted:
            raise Gone

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, wiki)
        return wiki


class WikiVersionDetail(JSONAPIBaseView, generics.RetrieveAPIView, WikiVersionMixin):
    """Details about a specific wiki version. *Read-only*.

    ###Permissions

    Wiki versions on public nodes are given read-only access to everyone. Wiki versions on private nodes are only visible to
    contributors and administrators on the parent node.

    Note that if an anonymous view_only key is being used, the user relationship will not be exposed.

    ##Attributes

    OSF wiki entities have the "wikis" `type`.

        name                        type                   description
        ======================================================================================================
        date_modified               iso8601 timestamp      timestamp when the wiki version was last updated
        content_type                string                 MIME-type
        identifier                  integer                version number of the wiki

    ##Relationships

    ###User

    The user who created the wiki version.

    ###WikiPage

    The wiki that this version belongs to

    ##Links

        self:  the canonical api endpoint of this wiki
        download: the link to retrive the contents of the wiki version

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

    serializer_class = WikiVersionSerializer

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'wiki-versions'
    view_name = 'wiki-version-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_wiki_version()
