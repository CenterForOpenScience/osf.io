from rest_framework import generics
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN, HTTP_400_BAD_REQUEST
from rest_framework import permissions as drf_permissions

from modularodm import Q

from framework.exceptions import PermissionsError
from framework.auth.oauth_scopes import CoreScopes

from website.models import Node

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.filters import ODMFilterMixin
from api.base.parsers import JSONAPIOnetoOneRelationshipParser, JSONAPIOnetoOneRelationshipParserForRegularJSON
from api.preprints.parsers import PreprintsJSONAPIParser, PreprintsJSONAPIParserForRegularJSON
from api.preprints.serializers import PreprintSerializer, PreprintDetailSerializer, PreprintDetailRetrieveSerializer, PreprintPreprintProviderRelationshipSerializer
from api.nodes.views import NodeMixin, WaterButlerMixin, NodeContributorsList, NodeContributorsSerializer
from api.base.utils import get_object_or_error
from rest_framework.exceptions import NotFound


class PreprintMixin(NodeMixin):
    serializer_class = PreprintSerializer
    node_lookup_url_kwarg = 'node_id'

    def get_node(self):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            display_name='preprint'
        )
        if not node.is_preprint and self.request.method != 'POST':
            raise NotFound

        return node


class PreprintList(JSONAPIBaseView, generics.ListCreateAPIView, ODMFilterMixin):
    """Preprints that represent a special kind of preprint node. *Writeable*.

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

    Preprints may be filtered by their `id`, `title`, `public`, `tags`, `date_created`, `date_modified`, `provider`, and `subjects`
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

    ###Creating New Preprints

    Create a new preprint by posting to the guid of the existing **node**, including the file_id for the
    file you'd like to make the primary preprint file. Note that the **node id** will not be accessible via the
    preprints detail view until after the preprint has been created.

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
    )
    parser_classes = (PreprintsJSONAPIParser, PreprintsJSONAPIParserForRegularJSON,)

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintSerializer

    view_category = 'preprints'
    view_name = 'preprint-detail'

    def get_object(self):
        return self.get_node()


class PreprintContributorsList(NodeContributorsList, PreprintMixin):
    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NODE_PREPRINTS_WRITE]

    view_category = 'preprint'
    view_name = 'preprint-contributors'

    serializer_class = NodeContributorsSerializer


class PreprintToPreprintProviderRelationship(JSONAPIBaseView, generics.RetrieveUpdateAPIView, PreprintMixin):
    """ Relationship Endpoint for Preprint -> PreprintProvider

    Used to set preprint_provider of a preprint to a PreprintProvider

    ##Actions

    ###Get

        Method:        GET
        URL:           /links/self
        Query Params:  <none>
        Success:       200

    ###Create

        Method:        PUT
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "preprint_provider",   # required
                           "id": <provider_id>   # required
                         }
                       }
        Success:       200

    This requires admin permissions in the node.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]
    serializer_class = PreprintPreprintProviderRelationshipSerializer
    parser_classes = (JSONAPIOnetoOneRelationshipParser, JSONAPIOnetoOneRelationshipParserForRegularJSON, )

    view_category = 'preprints'
    view_name = 'preprint-relationships-preprint_provider'

    def get_object(self):
        preprint = self.get_node()
        obj = {
            'data': preprint.preprint_provider,
            'self': preprint
        }
        return obj

    def update(self, *args, **kwargs):
        try:
            ret = super(PreprintToPreprintProviderRelationship, self).update(*args, **kwargs)
        except PermissionsError:
            return Response(status=HTTP_403_FORBIDDEN)
        except ValueError:
            return Response(status=HTTP_400_BAD_REQUEST)
        return ret
