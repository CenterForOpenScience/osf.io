from modularodm import Q
from rest_framework import generics
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework import permissions as drf_permissions

from website.models import Node
from framework.auth.oauth_scopes import CoreScopes

from api.base.views import JSONAPIBaseView
from api.base.filters import ODMFilterMixin
from api.base.utils import get_object_or_error
from api.base import permissions as base_permissions
from api.base.exceptions import RelationshipPostMakesNoChanges
from api.base.parsers import JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON
from api.preprint_providers.serializers import PreprintProviderSerializer
from api.preprints.parsers import PreprintsJSONAPIParser, PreprintsJSONAPIParserForRegularJSON
from api.preprints.serializers import PreprintSerializer, PreprintPreprintProvidersRelationshipSerializer
from api.nodes.views import NodeMixin, WaterButlerMixin
from api.nodes.permissions import ContributorOrPublic


class PreprintMixin(NodeMixin):
    serializer_class = PreprintSerializer
    node_lookup_url_kwarg = 'node_id'

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            display_name='preprint'
        )
        if not node.is_preprint and self.request.method != 'POST':
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)

        return node


class PreprintList(JSONAPIBaseView, generics.ListCreateAPIView, ODMFilterMixin):
    """Preprints that represent a special kind of preprint node. *Writeable*.

    ##Note
    **This API endpoint is under active development, and is subject to change in the future.**

    Paginated list of preprints ordered by their `date_created`.  Each resource contains a representation of the
    preprint.

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

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Preprints may be filtered by their `id`, `title`, `public`, `tags`, `date_created`, `date_modified`, and `subjects`
    Most are string fields and will be filtered using simple substring matching.

    ###Creating New Preprints

    Create a new preprint by posting to the guid of the existing **node**, including the file_id for the
    file you'd like to make the primary preprint file. Note that the **node id** will not be accessible via the
    preprints detail view until after the preprint has been created.

        Method:        POST
        URL:           /preprints/
        Query Params:  <none>
        Body (JSON):   {
                        "data": {
                            "id": node_id,
                            "attributes": {
                                "subjects":      [{subject_id}, ...]  # required
                                "description":   {description},       # optional
                                "tags":          [{tag1}, ...],       # optional
                                "provider":      {provider}           # optional
                            },
                            "relationships": {
                                "primary_file": {                     # required
                                    "data": {
                                        "type": "primary",
                                        "id": {file_id}
                                    }
                                }
                            }
                        }
                    }
        Success:       201 CREATED + preprint representation

    New preprints are created by issuing a POST request to this endpoint, along with the guid for the node to create a preprint from.
    Provider defaults to osf.

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
    )

    parser_classes = (PreprintsJSONAPIParser, PreprintsJSONAPIParserForRegularJSON,)

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintSerializer

    ordering = ('-date_created')
    view_category = 'preprints'
    view_name = 'preprint-list'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('preprint_file', 'ne', None) &
            Q('is_deleted', 'ne', True) &
            Q('is_public', 'eq', True)
        )

    # overrides ListAPIView
    def get_queryset(self):
        nodes = Node.find(self.get_query_from_request())
        return (node for node in nodes if node.is_preprint)

class PreprintDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, PreprintMixin, WaterButlerMixin):
    """Preprint Detail  *Writeable*.

    ##Note
    **This API endpoint is under active development, and is subject to change in the future.**

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
        provider                        string                original source of the preprint
        doi                             string                bare DOI for the manuscript, as entered by the user

    ###Updating Preprints

    Update a preprint by sending a patch request to the guid of the existing preprint node that you'd like to update.

        Method:        PATCH
        URL:           /preprints/{node_id}/
        Query Params:  <none>
        Body (JSON):   {
                        "data": {
                            "id": node_id,
                            "attributes": {
                                "subjects":      [{subject_id}, ...]  # optional
                                "description":   {description},       # optional
                                "tags":          [{tag}, ...],        # optional
                                "provider":      {provider}           # optional
                            },
                            "relationships": {
                                "primary_file": {                     # optional
                                    "data": {
                                        "type": "primary",
                                        "id": {file_id}
                                    }
                                }
                            }
                        }
                    }
        Success:       200 OK + preprint representation

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
    )
    parser_classes = (PreprintsJSONAPIParser, PreprintsJSONAPIParserForRegularJSON,)

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintSerializer

    view_category = 'preprints'
    view_name = 'preprint-detail'

    def get_object(self):
        return self.get_node()


class PreprintPreprintProvidersList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin, NodeMixin):
    """ Detail of the preprint providers a preprint has, if any. Returns [] if the preprint has no
    preprnt providers.

    ##Note
    **This API endpoint is under active development, and is subject to change in the future**

    ##Attributes

    OSF Preprint Providers have the "preprint_providers" `type`.

        name           type               description
        =========================================================================
        name           string             name of the preprint provider
        logo_path      string             a path to the preprint provider's static logo
        banner_path    string             a path to the preprint provider's banner
        description    string             description of the preprint provider

    ##Links

        self: the canonical api endpoint of this preprint provider
        preprints: link to the provider's preprints

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = PreprintProviderSerializer

    view_category = 'preprints'
    view_name = 'preprint-preprint_providers'

    def get_queryset(self):
        node = self.get_node()
        return node.preprint_providers


class PreprintToPreprintProviderRelationship(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, generics.CreateAPIView, PreprintMixin):
    """ Relationship Endpoint for Preprint -> PreprintProvider

    Used to set preprint_provider of a preprint to a PreprintProvider

    ##Note
    **This API endpoint is under active development, and is subject to change in the future.**

    ##Actions

    ###Get

        Method:        GET
        URL:           /links/self
        Query Params:  <none>
        Success:       200

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [
                             {
                               "type": "preprint_providers",   # required
                               "id": <provider_id>   # required
                             }
                         ]
                       }
        Success:       201

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "preprint_providers",   # required
                           "id": <provider_id>   # required
                         }]
                       }
        Success:       200

        This will delete all preprint_providers not listed, meaning a data: [] payload
        does the same as a DELETE with all the preprint_providers.

    ###Destroy

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "preprint_providers",   # required
                           "id": <provider_id>   # required
                         }]
                       }
        Success:       204

    All of these methods require admin permissions in the preprint.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintPreprintProvidersRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    view_category = 'preprints'
    view_name = 'preprint-relationships-preprint_providers'

    def get_object(self):
        preprint = self.get_node()
        obj = {
            'data': preprint.preprint_providers,
            'self': preprint
        }
        return obj

    def perform_destroy(self, instance):
        data = self.request.data['data']
        user = self.request.user
        current_providers = {provider._id: provider for provider in instance['data']}
        node = instance['self']

        if not node.has_permission(user, 'admin'):
            raise exceptions.PermissionDenied(
                detail='User must be an admin to delete the PreprintProvider relationship.'
            )

        for val in data:
            if val['id'] in current_providers:
                node.remove_preprint_provider(preprint_provider=current_providers[val['id']], user=user)
        node.save()

    def create(self, *args, **kwargs):
        try:
            ret = super(PreprintToPreprintProviderRelationship, self).create(*args, **kwargs)
        except RelationshipPostMakesNoChanges:
            return Response(status=HTTP_204_NO_CONTENT)
        return ret
