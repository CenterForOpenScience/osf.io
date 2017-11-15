from rest_framework import generics, permissions as drf_permissions

from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.filters import ListFilterMixin
from api.base.pagination import NoMaxPageSizePagination
from api.base import permissions as base_permissions
from api.base.versioning import DeprecatedEndpointMixin
from api.taxonomies.serializers import TaxonomySerializer
from osf.models import Subject
from framework.auth.oauth_scopes import CoreScopes


class TaxonomyList(DeprecatedEndpointMixin, JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    '''[BePress taxonomy subject](https://www.bepress.com/wp-content/uploads/2016/12/Digital-Commons-Disciplines-taxonomy-2017-01.pdf) instance. *Read-only*

    ##Note
    **This API endpoint is under active development, and is subject to change in the future**

    ##Taxonomy Attributes

        name           type                   description
        ----------------------------------------------------------------------------
        text           array of strings       Actual text of the subject
        parents        array of subjects      Parent subjects, [] indicates a top level subject.

    ##Query Params

    + `field['id']=<subject_id>` -- Finds one subject with the given id
    + `field['text']=<Str>` -- Find subjects with texts that match the passed string

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.
    + `filter['parents']=<subject_id>` -- Find subjects that have a parent with the id passed
    + `filter['parents']=null` -- Find top level subjects

    Subjects may be filtered by their 'text', 'parents', and 'id' fields.

    **Note:** Subjects are unique per provider (e.g. there exists at most one object per provider with any given `text`.
    '''
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
        return Subject.objects.all()

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
    '''[BePress taxonomy subject](https://www.bepress.com/wp-content/uploads/2016/12/Digital-Commons-Disciplines-taxonomy-2017-01.pdf) instance. *Read-only*

    ##Note
    **This API endpoint is under active development, and is subject to change in the future**

    ##Taxonomy Attributes

    See TaxonomyList

    **Note:** Subjects are unique per provider (e.g. there exists at most one object per provider with any given `text`.
    '''
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
        return get_object_or_error(Subject, self.kwargs['taxonomy_id'], self.request)
