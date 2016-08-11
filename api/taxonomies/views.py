from rest_framework import generics, permissions as drf_permissions
from rest_framework import serializers as ser

from modularodm import Q

from api.base.views import JSONAPIBaseView
from api.base.filters import ODMFilterMixin
from api.base import permissions as base_permissions
from api.taxonomies.serializers import TaxonomySerializer
from website.project.taxonomies import Subject
from framework.auth.oauth_scopes import CoreScopes


class Taxonomy(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    '''[PLOS taxonomy of subjects](http://journals.plos.org/plosone/browse/) in flattened form. *Read-only*

    ##Taxonomy Attributes

        name           type                   description
        ----------------------------------------------------------------------------
        text           array of strings       Actual text of the subject
        type           string                 Origin of the subject term - all PLOS for now
        parent_ids     array of strings       IDs of the parent subjects, [] indicates a top level subject.

    ##Query Params

    + `field['id']=<subject_id>` -- Finds one subject with the given id
    + `field['text']=<Str>` -- Find subjects with texts that match the passed string

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.
    + `filter['parent_ids']=<subject_id>` -- Find subjects that have a parent with the id passed
    + `filter['parent_ids']=null` -- Find top level subjects

    Subjects may be filtered by their 'text', 'parent_ids', 'type' and 'id' fields.

    **Note:** Subjects are unique (e.g. there exists only one object in this list with `text='Biology and life sciences'`),
    but as per the structure of the PLOS taxonomy, subjects can exist in separate paths down the taxonomy and as such
    can have multiple parent subjects.

    Only the top three levels of the PLOS taxonomy are included.
    '''
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope
    )

    DEFAULT_OPERATOR_OVERRIDES = {
        ser.CharField: 'icontains',
        ser.ListField: 'eq',
    }

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = TaxonomySerializer
    view_category = 'taxonomies'
    view_name = 'taxonomy'

    # overrides ListAPIView
    def get_default_odm_query(self):
        return Q('type', 'ne', None)

    def get_queryset(self):
        return Subject.find(self.get_query_from_request())
