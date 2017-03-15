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
            display_name='preprint',
            prefetch_fields=self.serializer_class().model_field_names
        )
        if not preprint:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, preprint)

        return preprint


class PreprintList(JSONAPIBaseView, generics.ListCreateAPIView, ODMFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Preprints_preprints_list).
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
                operation['op'] = 'iexact'

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
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Preprints_preprints_read).
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
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Preprints_preprints_citation_list).
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
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Preprints_preprints_citation_read).
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
