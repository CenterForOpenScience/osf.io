import re

from modularodm import Q
from rest_framework import generics
from rest_framework.exceptions import NotFound, PermissionDenied, NotAuthenticated
from rest_framework import permissions as drf_permissions

from website.models import PreprintService
from framework.auth.oauth_scopes import CoreScopes

from api.base.exceptions import Conflict
from api.base.views import JSONAPIBaseView
from api.base.filters import ODMFilterMixin
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.utils import get_object_or_error, get_user_auth
from api.base import permissions as base_permissions
from api.citations.utils import render_citation, preprint_csl
from api.preprints.serializers import (
    PreprintSerializer,
    PreprintCreateSerializer,
    PreprintCitationSerializer,
)
from api.nodes.serializers import (
    NodeCitationStyleSerializer,
)
from api.nodes.views import NodeMixin, WaterButlerMixin
from api.nodes.permissions import ContributorOrPublic


class PreprintMixin(NodeMixin):
    serializer_class = PreprintSerializer
    preprint_lookup_url_kwarg = 'preprint_id'

    def get_preprint(self, check_object_permissions=True):
        preprint = get_object_or_error(
            PreprintService,
            self.kwargs[self.preprint_lookup_url_kwarg],
            display_name='preprint'
        )
        if not preprint:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, preprint)

        return preprint


class PreprintList(JSONAPIBaseView, generics.ListCreateAPIView, ODMFilterMixin):
    """Preprints that represent a special kind of preprint node. *Writeable*.

    Paginated list of preprints ordered by their `date_created`.  Each resource contains a representation of the
    preprint.

    ##Preprint Attributes

    OSF Preprint entities have the "preprints" `type`.

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the preprint was created
        date_modified                   iso8601 timestamp                   timestamp that the preprint was last modified
        date_published                  iso8601 timestamp                   timestamp when the preprint was published
        is_published                    boolean                             whether or not this preprint is published
        is_preprint_orphan              boolean                             whether or not this preprint is orphaned
        subjects                        list of lists of dictionaries       ids of Subject in the PLOS taxonomy. Dictionary, containing the subject text and subject ID
        doi                             string                              bare DOI for the manuscript, as entered by the user

    ##Relationships

    ###Node
    The node that this preprint was created for

    ###Primary File
    The file that is designated as the preprint's primary file, or the manuscript of the preprint.

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

    Preprints may be filtered by their `id`, `is_published`, `date_created`, `date_modified`, `provider`
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
                            "attributes": {},
                            "relationships": {
                                "node": {                           # required
                                    "data": {
                                        "type": "nodes",
                                        "id": {node_id}
                                    }
                                },
                                "primary_file": {                   # required
                                    "data": {
                                        "type": "primary_files",
                                        "id": {file_id}
                                    }
                                },
                                "provider": {                       # required
                                    "data": {
                                        "type": "providers",
                                        "id": {provider_id}
                                    }
                                },
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

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintSerializer

    ordering = ('-date_created')
    view_category = 'preprints'
    view_name = 'preprint-list'

    # overrides FilterMixin
    def postprocess_query_param(self, key, field_name, operation):
        # tag queries will usually be on Tag.name,
        # ?filter[tags]=foo should be translated to Q('tags__name', 'eq', 'foo')
        # But queries on lists should be tags, e.g.
        # ?filter[tags]=foo,bar should be translated to Q('tags', 'isnull', True)
        # ?filter[tags]=[] should be translated to Q('tags', 'isnull', True)
        if field_name == 'tags':
            if operation['value'] not in (list(), tuple()):
                operation['source_field_name'] = 'tags__name'

        if field_name == 'provider':
            operation['source_field_name'] = 'provider___id'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PreprintCreateSerializer
        else:
            return PreprintSerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('node', 'ne', None)
        )

    # overrides ListAPIView
    def get_queryset(self):
        return PreprintService.find(self.get_query_from_request())

class PreprintDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, PreprintMixin, WaterButlerMixin):
    """Preprint Detail  *Writeable*.

    ##Preprint Attributes

    OSF Preprint entities have the "preprints" `type`.

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the preprint was created
        date_modified                   iso8601 timestamp                   timestamp that the preprint was last modified
        date_published                  iso8601 timestamp                   timestamp when the preprint was published
        is_published                    boolean                             whether or not this preprint is published
        is_preprint_orphan              boolean                             whether or not this preprint is orphaned
        subjects                        array of tuples of dictionaries     ids of Subject in the PLOS taxonomy. Dictionary, containing the subject text and subject ID
        doi                             string                              bare DOI for the manuscript, as entered by the user

    ##Relationships

    ###Node
    The node that this preprint was created for

    ###Primary File
    The file that is designated as the preprint's primary file, or the manuscript of the preprint.

    ###Provider
    Link to preprint_provider detail for this preprint

    ##Links
    - `self` -- Preprint detail page for the current preprint
    - `html` -- Project on the OSF corresponding to the current preprint
    - `doi` -- URL representation of the DOI entered by the user for the preprint manuscript

    ##Updating Preprints

    Update a preprint by sending a patch request to the guid of the existing preprint node that you'd like to update.

        Method:        PATCH
        URL:           /preprints/{node_id}/
        Query Params:  <none>
        Body (JSON):   {
                        "data": {
                            "id": node_id,
                            "attributes": {
                                "subjects":     [({root_subject_id}, {child_subject_id}), ...]  # optional
                                "is_published": true,                                           # optional
                                "doi":          {valid_doi}                                     # optional
                            },
                            "relationships": {
                                "primary_file": {                                               # optional
                                    "data": {
                                        "type": "primary_files",
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
    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintSerializer

    view_category = 'preprints'
    view_name = 'preprint-detail'

    def get_object(self):
        return self.get_preprint()

    def perform_destroy(self, instance):
        if instance.is_published:
            raise Conflict('Published preprints cannot be deleted.')
        PreprintService.remove_one(instance)


class PreprintCitationDetail(JSONAPIBaseView, generics.RetrieveAPIView, PreprintMixin):
    """ The citation details for a preprint, in CSL format *Read Only*

    ##PreprintCitationDetail Attributes

        name                     type                description
        =================================================================================
        id                       string               unique ID for the citation
        title                    string               title of project or component
        author                   list                 list of authors for the preprint
        publisher                string               publisher - the preprint provider
        type                     string               type of citation - web
        doi                      string               doi of the resource

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CITATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = PreprintCitationSerializer
    view_category = 'preprints'
    view_name = 'preprint-citation'

    def get_object(self):
        preprint = self.get_preprint()
        auth = get_user_auth(self.request)

        if preprint.node.is_public or preprint.node.can_view(auth) or preprint.is_published:
            return preprint_csl(preprint, preprint.node)

        raise PermissionDenied if auth.user else NotAuthenticated


class PreprintCitationStyleDetail(JSONAPIBaseView, generics.RetrieveAPIView, PreprintMixin):
    """ The citation for a preprint in a specific style's format. *Read Only*

    ##NodeCitationDetail Attributes

        name                     type                description
        =================================================================================
        citation                string               complete citation for a preprint in the given style

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CITATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeCitationStyleSerializer
    view_category = 'preprint'
    view_name = 'preprint-citation'

    def get_object(self):
        preprint = self.get_preprint()
        auth = get_user_auth(self.request)
        style = self.kwargs.get('style_id')

        if preprint.node.is_public or preprint.node.can_view(auth) or preprint.is_published:
            try:
                citation = render_citation(node=preprint, style=style)
            except ValueError as err:  # style requested could not be found
                csl_name = re.findall('[a-zA-Z]+\.csl', err.message)[0]
                raise NotFound('{} is not a known style.'.format(csl_name))

            return {'citation': citation, 'id': style}

        raise PermissionDenied if auth.user else NotAuthenticated
