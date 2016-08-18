from rest_framework import generics
from rest_framework import permissions as drf_permissions

from modularodm import Q

from framework.auth.oauth_scopes import CoreScopes

from website.models import Node, PreprintProvider

from api.base import permissions as base_permissions
from api.base.filters import ODMFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.pagination import MaxSizePagination

from api.preprint_providers.serializers import PreprintProviderSerializer
from api.preprints.serializers import PreprintSerializer


class PreprintProviderMixin(object):
    institution_lookup_url_kwarg = 'institution_id'

    def get_preprintprovider(self):
        provider = get_object_or_error(
            PreprintProvider,
            self.kwargs[self.institution_lookup_url_kwarg],
            display_name='institution'
        )
        return provider


class PreprintProviderList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """
    Paginated list of verified PreprintProviders available

    ##PreprintProvider Attributes

    OSF Institutions have the "institutions" `type`.

        name           type               description
        =========================================================================
        name           string             title of the preprint provider
        id             string             unique identifier in the OSF
        logo_path      string             a path to the preprint provider's static logo
        banner_path    string             a path to the preprint provider's static banner

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = PreprintProvider

    pagination_class = MaxSizePagination
    serializer_class = PreprintProviderSerializer
    view_category = 'preprint_providers'
    view_name = 'preprint_providers-list'

    ordering = ('name', )

    def get_default_odm_query(self):
        return Q('_id', 'ne', None)

    # overrides ListAPIView
    def get_queryset(self):
        return PreprintProvider.find(self.get_query_from_request())


class PreprintProviderDetail(JSONAPIBaseView, generics.RetrieveAPIView, PreprintProviderMixin):
    """ Details about a given preprint provider.

    ##Attributes

    Preprint Providers have the "preprint_providers" `type`.

        name           type               description
        =========================================================================
        name           string             title of the preprint provider
        id             string             unique identifier in the OSF
        logo_path      string             a path to the preprint provider's static logo
        banner_path    string             a path to the preprint provider's static banner

    ##Links

        self:  the canonical api endpoint of this institution
        html:  this institution's page on the OSF website

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = PreprintProvider

    serializer_class = PreprintProviderSerializer
    view_category = 'preprint_providers'
    view_name = 'preprint_provider-detail'

    def get_object(self):
        return PreprintProvider.load(self.kwargs['provider_id'])


class PreprintProviderPreprintList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """Preprints from a given preprint_provider. *Read Only*

    To update preprints with a given preprint_provider, see the `<node_id>/relationships/preprint_provider` endpoint

    ##Preprint Attributes

    Many of these preprint attributes are the same as node, with a few special fields added in.

    OSF Preprint entities have the "preprint" `type`.

        name                            type                  description
        ====================================================================================
        title                           string                title of preprint, same as its project or component
        abstract                        string                description of the preprint
        date_created                    iso8601 timestamp     timestamp that the preprint was created
        date_modified                   iso8601 timestamp     timestamp when the preprint was last updated
        tags                            array of strings      list of tags that describe the node
        subjects                        array of dictionaries list ids of Subject in the PLOS taxonomy. Dictrionary, containing the subject text and subject ID
        doi                             string                bare DOI for the manuscript, as entered by the user

    ##Relationships

    ###Primary File
    The file that is designated as the preprint's primary file, or the manuscript of the preprint.

    ###Files
    Link to list of files associated with this node/preprint

    ###Contributors
    Link to list of contributors that are affiliated with this preprint.

    ###Provider
    Link to preprint_provider detail for this preprint

    ##Links

    - `self` -- Preprint detail page for the current preprint
    - `html` -- Project on the OSF corresponding to the current preprint
    - `doi` -- URL representation of the DOI entered by the user for the preprint manuscript

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).
    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    ordering = ('-date_created')

    serializer_class = PreprintSerializer

    required_read_scopes = [CoreScopes.NODE_FILE_READ]

    view_category = 'preprints'
    view_name = 'preprints-list'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        provider = PreprintProvider.find_one(Q('_id', 'eq', self.kwargs['provider_id']))
        return (
            Q('preprint_file', 'ne', None) &
            Q('is_deleted', 'ne', True) &
            Q('preprint_file', 'ne', None) &
            Q('is_public', 'eq', True) &
            Q('preprint_provider', 'eq', provider)
        )

    # overrides ListAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        nodes = Node.find(query)

        return [node for node in nodes if node.is_preprint]
