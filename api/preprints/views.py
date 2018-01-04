import re

from rest_framework import generics
from rest_framework.exceptions import NotFound, PermissionDenied, NotAuthenticated
from rest_framework import permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes
from osf.models import ReviewAction, PreprintService
from osf.utils.requests import check_select_for_update

from api.actions.permissions import ReviewActionPermission
from api.actions.serializers import ReviewActionSerializer
from api.actions.views import get_review_actions_queryset
from api.base.exceptions import Conflict
from api.base.views import JSONAPIBaseView, WaterButlerMixin
from api.base.filters import ListFilterMixin, PreprintFilterMixin
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.utils import absolute_reverse, get_user_auth
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

from api.identifiers.views import IdentifierList
from api.identifiers.serializers import PreprintIdentifierSerializer
from api.nodes.views import NodeMixin, NodeContributorsList
from api.nodes.permissions import ContributorOrPublic

from api.preprints.permissions import PreprintPublishedOrAdmin


class PreprintMixin(NodeMixin):
    serializer_class = PreprintSerializer
    preprint_lookup_url_kwarg = 'preprint_id'

    def get_preprint(self, check_object_permissions=True):
        qs = PreprintService.objects.filter(guids___id=self.kwargs[self.preprint_lookup_url_kwarg])
        try:
            preprint = qs.select_for_update().get() if check_select_for_update(self.request) else qs.select_related('node').get()
        except PreprintService.DoesNotExist:
            raise NotFound

        if preprint.node.is_deleted:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, preprint)

        return preprint


class PreprintList(JSONAPIBaseView, generics.ListCreateAPIView, PreprintFilterMixin):
    """Preprints that represent a special kind of preprint node. *Writeable*.

    Paginated list of preprints ordered by their `created`.  Each resource contains a representation of the
    preprint.

    ##Preprint Attributes

    OSF Preprint entities have the "preprints" `type`.

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the preprint was created
        date_modified                   iso8601 timestamp                   timestamp that the preprint was last modified
        date_published                  iso8601 timestamp                   timestamp when the preprint was published
        original_publication_date       iso8601 timestamp                   user-entered date of publication from external posting
        is_published                    boolean                             whether or not this preprint is published
        is_preprint_orphan              boolean                             whether or not this preprint is orphaned
        subjects                        list of lists of dictionaries       ids of Subject in the BePress taxonomy. Dictionary, containing the subject text and subject ID
        doi                             string                              bare DOI for the manuscript, as entered by the user
        preprint_doi_created            iso8601 timestamp                   timestamp that the preprint doi was created

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
    - `preprint_doi` -- DOI URL for the current preprint.

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
    # These permissions are not checked for the list of preprints, permissions handled by the query
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
    )

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintSerializer

    ordering = ('-created')
    ordering_fields = ('created', 'date_last_transitioned')
    view_category = 'preprints'
    view_name = 'preprint-list'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PreprintCreateSerializer
        else:
            return PreprintSerializer

    def get_default_queryset(self):
        auth = get_user_auth(self.request)
        auth_user = getattr(auth, 'user', None)

        # Permissions on the list objects are handled by the query
        return self.preprints_queryset(PreprintService.objects.all(), auth_user)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()

class PreprintDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, PreprintMixin, WaterButlerMixin):
    """Preprint Detail  *Writeable*.

    ##Preprint Attributes

    OSF Preprint entities have the "preprints" `type`.

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the preprint was created
        date_modified                   iso8601 timestamp                   timestamp that the preprint was last modified
        date_published                  iso8601 timestamp                   timestamp when the preprint was published
        original_publication_date       iso8601 timestamp                   user-entered date of publication from external posting
        is_published                    boolean                             whether or not this preprint is published
        is_preprint_orphan              boolean                             whether or not this preprint is orphaned
        subjects                        array of tuples of dictionaries     ids of Subject in the BePress taxonomy. Dictionary, containing the subject text and subject ID
        doi                             string                              bare DOI for the manuscript, as entered by the user
        preprint_doi_created            iso8601 timestamp                   timestamp that the preprint doi was created

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
        PreprintPublishedOrAdmin,
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

class PreprintIdentifierList(IdentifierList, PreprintMixin):
    """List of identifiers for a specified preprint. *Read-only*.

    ##Identifier Attributes

    OSF Identifier entities have the "identifiers" `type`.

        name           type                   description
        ----------------------------------------------------------------------------
        category       string                 e.g. 'ark', 'doi'
        value          string                 the identifier value itself

    ##Links

        self: this identifier's detail page

    ##Relationships

    ###Referent

    The identifier is refers to this preprint.

    ##Actions

    *None*.

    ##Query Params

     Identifiers may be filtered by their category.

    #This Request/Response

    """

    permission_classes = (
        PreprintPublishedOrAdmin,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    serializer_class = PreprintIdentifierSerializer
    required_read_scopes = [CoreScopes.IDENTIFIERS_READ]
    required_write_scopes = [CoreScopes.NULL]

    preprint_lookup_url_kwarg = 'preprint_id'

    view_category = 'identifiers'
    view_name = 'identifier-list'

    # overrides IdentifierList
    def get_object(self, check_object_permissions=True):
        return self.get_preprint(check_object_permissions=check_object_permissions)


class PreprintContributorsList(NodeContributorsList, PreprintMixin):

    def create(self, request, *args, **kwargs):
        self.kwargs['node_id'] = self.get_preprint(check_object_permissions=False).node._id
        return super(PreprintContributorsList, self).create(request, *args, **kwargs)


class PreprintActionList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, PreprintMixin):
    """Action List *Read-only*

    Actions represent state changes and/or comments on a reviewable object (e.g. a preprint)

    ##Action Attributes

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the action was created
        date_modified                   iso8601 timestamp                   timestamp that the action was last modified
        from_state                      string                              state of the reviewable before this action was created
        to_state                        string                              state of the reviewable after this action was created
        comment                         string                              comment explaining the state change
        trigger                         string                              name of the trigger for this action

    ##Relationships

    ###Target
    Link to the object (e.g. preprint) this action acts on

    ###Provider
    Link to detail for the target object's provider

    ###Creator
    Link to the user that created this action

    ##Links
    - `self` -- Detail page for the current action

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Actions may be filtered by their `id`, `from_state`, `to_state`, `date_created`, `date_modified`, `creator`, `provider`, `target`
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReviewActionPermission,
    )

    required_read_scopes = [CoreScopes.ACTIONS_READ]
    required_write_scopes = [CoreScopes.ACTIONS_WRITE]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)
    serializer_class = ReviewActionSerializer
    model_class = ReviewAction

    ordering = ('-created',)
    view_category = 'preprints'
    view_name = 'preprint-review-action-list'

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        target = serializer.validated_data['target']
        self.check_object_permissions(self.request, target)

        if not target.provider.is_reviewed:
            raise Conflict('{} is an unmoderated provider. If you are an admin, set up moderation by setting `reviews_workflow` at {}'.format(
                target.provider.name,
                absolute_reverse('preprint_providers:preprint_provider-detail', kwargs={
                    'provider_id': target.provider._id,
                    'version': self.request.parser_context['kwargs']['version']
                })
            ))

        serializer.save(user=self.request.user)

    # overrides ListFilterMixin
    def get_default_queryset(self):
        return get_review_actions_queryset().filter(target_id=self.get_preprint().id)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()
