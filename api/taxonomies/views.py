from rest_framework import generics, permissions as drf_permissions

from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.filters import ODMFilterMixin
from api.base.pagination import NoMaxPageSizePagination
from api.base import permissions as base_permissions
from api.taxonomies.serializers import TaxonomySerializer
from website.project.taxonomies import Subject
from framework.auth.oauth_scopes import CoreScopes


class TaxonomyList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    '''[PLOS taxonomy of subjects](http://journals.plos.org/plosone/browse/) in flattened form. *Read-only*

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

    **Note:** Subjects are unique (e.g. there exists only one object in this list with `text='Biology and life sciences'`),
    but as per the structure of the PLOS taxonomy, subjects can exist in separate paths down the taxonomy and as such
    can have multiple parent subjects.

    Only the top three levels of the PLOS taxonomy are included.
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

    # overrides ListAPIView
    def get_default_odm_query(self):
        return

    def get_queryset(self):
        return Subject.find(self.get_query_from_request())

class TaxonomyDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    '''[PLOS taxonomy subject](http://journals.plos.org/plosone/browse/) instance. *Read-only*

    ##Note
    **This API endpoint is under active development, and is subject to change in the future**

    ##Taxonomy Attributes

    See TaxonomyList

    **Note:** Subjects are unique (e.g. there exists only one object in this list with `text='Biology and life sciences'`),
    but as per the structure of the PLOS taxonomy, subjects can exist in separate paths down the taxonomy and as such
    can have multiple parent subjects.

    Only the top three levels of the PLOS taxonomy are included.
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
        return get_object_or_error(Subject, self.kwargs['taxonomy_id'])
