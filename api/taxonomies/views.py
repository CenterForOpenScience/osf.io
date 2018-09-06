from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from django.core.exceptions import ObjectDoesNotExist

from api.base.views import JSONAPIBaseView, DeprecatedView
from api.base.filters import ListFilterMixin
from api.base.pagination import NoMaxPageSizePagination
from api.base import permissions as base_permissions
from api.taxonomies.serializers import TaxonomySerializer
from api.taxonomies.utils import optimize_subject_query
from osf.models import Subject
from framework.auth.oauth_scopes import CoreScopes


class TaxonomyList(DeprecatedView, JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/taxonomies_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = TaxonomySerializer
    pagination_class = NoMaxPageSizePagination
    view_category = 'taxonomies'
    view_name = 'taxonomy-list'
    max_version = '2.5'

    ordering = ('-id',)

    def get_default_queryset(self):
        return optimize_subject_query(Subject.objects.all())

    def get_queryset(self):
        return self.get_queryset_from_request()

    # overrides FilterMixin
    def postprocess_query_param(self, key, field_name, operation):
        # TODO: Queries on 'parents' should be deprecated
        if field_name == 'parents':
            if operation['value'] not in (list(), tuple()):
                operation['source_field_name'] = 'parent___id'
            else:
                if len(operation['value']) > 1:
                    operation['source_field_name'] = 'parent___id__in'
                elif len(operation['value']) == 1:
                    operation['source_field_name'] == 'parent___id'
                    operation['value'] = operation['value'][0]
                else:
                    operation['source_field_name'] = 'parent__isnull'
                    operation['value'] = True


class TaxonomyDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/taxonomies_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = TaxonomySerializer
    view_category = 'taxonomies'
    view_name = 'taxonomy-detail'

    def get_object(self):
        try:
            return optimize_subject_query(Subject.objects).get(_id=self.kwargs['taxonomy_id'])
        except ObjectDoesNotExist:
            raise NotFound
