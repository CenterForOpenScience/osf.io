from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from django.core.exceptions import ObjectDoesNotExist

from api.base.views import JSONAPIBaseView
from api.base.filters import ListFilterMixin
from api.base.pagination import NoMaxPageSizePagination
from api.base.parsers import JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON
from api.base import permissions as base_permissions
from api.subjects.serializers import SubjectSerializer, SubjectsRelationshipSerializer
from api.taxonomies.utils import optimize_subject_query
from osf.models import Subject
from framework.auth.oauth_scopes import CoreScopes


class SubjectMixin(object):
    """Mixin with convenience methods for retrieving the current subject based on the
    current URL. By default, fetches the current subject based on the subject_id kwarg.
    """
    subject_lookup_url_kwarg = 'subject_id'

    def get_subject(self, check_object_permissions=True):
        subject_id = self.kwargs[self.subject_lookup_url_kwarg]

        try:
            subject = optimize_subject_query(Subject.objects).get(_id=subject_id)
        except ObjectDoesNotExist:
            raise NotFound

        if check_object_permissions:
            self.check_object_permissions(self.request, subject)

        return subject


class BaseResourceSubjectsList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    permission_classes = ()

    required_read_scopes = []
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = SubjectSerializer
    model = Subject
    view_category = ''
    view_name = ''

    ordering = ('-id',)

    def get_resource(self):
        raise NotImplementedError()

    def get_queryset(self):
        return self.get_resource().subjects.all()


class SubjectRelationshipBaseView(JSONAPIBaseView, generics.RetrieveUpdateAPIView):
    """ Relationship Endpoint for Resource -> Subjects Relationship

    Used to update the subjects on a resource

    ##Actions

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "subjects",   # required
                           "id": <subject_id>   # required
                         }]
                       }
        Success:       200

        This requires write permissions on the resource. This will delete
        subjects not listed, meaning a data: [] payload deletes all the subjects.

    """
    serializer_class = SubjectsRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    def get_resource(self, check_object_permissions=True):
        raise NotImplementedError()

    def get_object(self):
        resource = self.get_resource(check_object_permissions=False)
        obj = {
            'data': resource.subjects.all(),
            'self': resource,
        }
        self.check_object_permissions(self.request, obj)
        return obj


class SubjectList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = SubjectSerializer
    pagination_class = NoMaxPageSizePagination
    view_category = 'subjects'
    view_name = 'subject-list'

    ordering = ('-id',)

    def get_default_queryset(self):
        return optimize_subject_query(Subject.objects.all())

    def get_queryset(self):
        return self.get_queryset_from_request()

    # overrides FilterMixin
    def postprocess_query_param(self, key, field_name, operation):
        if field_name == 'parent':
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


class SubjectDetail(JSONAPIBaseView, generics.RetrieveAPIView, SubjectMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/subjects_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    serializer_class = SubjectSerializer

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'subjects'
    view_name = 'subject-detail'

    def get_object(self):
        return self.get_subject()


class SubjectChildrenList(JSONAPIBaseView, generics.ListAPIView, SubjectMixin, ListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/subject_children_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = SubjectSerializer
    pagination_class = NoMaxPageSizePagination
    view_category = 'subjects'
    view_name = 'subject-children'

    ordering = ('-id',)

    def get_default_queryset(self):
        subject = self.get_subject()
        return optimize_subject_query(subject.children.all())

    def get_queryset(self):
        return self.get_queryset_from_request()
