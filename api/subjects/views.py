from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from django.core.exceptions import ObjectDoesNotExist

from api.base.views import JSONAPIBaseView
from api.base.filters import ListFilterMixin
from api.base.pagination import NoMaxPageSizePagination
from api.base import permissions as base_permissions
from api.subjects.serializers import SubjectSerializer
from api.taxonomies.utils import optimize_subject_query
from osf.models import Subject
from framework.auth.oauth_scopes import CoreScopes


class SubjectMixin(object):
    """Mixin with convenience methods for retrieving the current subject based on the
    current URL. By default, fetches the current subject based on the subject_id kwarg.
    """
    node_lookup_url_kwarg = 'subject_id'

    def get_subject(self, check_object_permissions=True):
        subject_id = self.kwargs['subject_id']

        try:
            subject = optimize_subject_query(Subject.objects).get(_id=subject_id)
        except ObjectDoesNotExist:
            raise NotFound

        if check_object_permissions:
            self.check_object_permissions(self.request, subject)

        return subject


class SubjectList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/subjects_list).
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
    view_name = 'subject-list'

    ordering = ('-id',)

    def get_default_queryset(self):
        return optimize_subject_query(Subject.objects.all())

    def get_queryset(self):
        return self.get_queryset_from_request()


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
