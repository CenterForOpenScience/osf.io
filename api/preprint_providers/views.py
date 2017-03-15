from rest_framework import generics
from rest_framework import permissions as drf_permissions

from modularodm import Q

from framework.auth.oauth_scopes import CoreScopes

from website.models import Node, Subject, PreprintService, PreprintProvider

from api.base import permissions as base_permissions
from api.base.filters import ODMFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.pagination import MaxSizePagination

from api.licenses.views import LicenseList
from api.taxonomies.serializers import TaxonomySerializer
from api.preprint_providers.serializers import PreprintProviderSerializer
from api.preprints.serializers import PreprintSerializer


class PreprintProviderList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Preprint_Providers_preprint_provider_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    model_class = PreprintProvider

    pagination_class = MaxSizePagination
    serializer_class = PreprintProviderSerializer
    view_category = 'preprint_providers'
    view_name = 'preprint_providers-list'

    ordering = ('name', )

    # implement ODMFilterMixin
    def get_default_odm_query(self):
        return None

    # overrides ListAPIView
    def get_queryset(self):
        return PreprintProvider.find(self.get_query_from_request())


class PreprintProviderDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Preprint_Providers_preprint_provider_detail).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    model_class = PreprintProvider

    serializer_class = PreprintProviderSerializer
    view_category = 'preprint_providers'
    view_name = 'preprint_provider-detail'

    def get_object(self):
        return PreprintProvider.load(self.kwargs['provider_id'])


class PreprintProviderPreprintList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Preprint_Providers_preprint_providers_preprints_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    ordering = ('-date_created')

    serializer_class = PreprintSerializer
    model_class = Node

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'preprint_providers'
    view_name = 'preprints-list'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        # TODO: this will return unpublished preprints so that users
        # can find and resume the publishing workflow, but filtering
        # public preprints should filter for `is_published`
        provider = PreprintProvider.find_one(Q('_id', 'eq', self.kwargs['provider_id']))
        return (
            Q('provider', 'eq', provider)
        )

    # overrides ListAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return PreprintService.find(query)


class PreprintProviderSubjectList(JSONAPIBaseView, generics.ListAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Preprint_Providers_preprint_provider_taxonomies_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'preprint_providers'
    view_name = 'taxonomy-list'

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = TaxonomySerializer

    def is_valid_subject(self, allows_children, allowed_parents, sub):
        if sub._id in allowed_parents:
            return True
        for parent in sub.parents.all():
            if parent._id in allows_children:
                return True
            for grandpa in parent.parents.all():
                if grandpa._id in allows_children:
                    return True
        return False

    def get_queryset(self):
        parent = self.request.query_params.get('filter[parents]', None)
        provider = PreprintProvider.load(self.kwargs['provider_id'])
        if parent:
            if parent == 'null':
                return provider.top_level_subjects
            #  Calculate this here to only have to do it once.
            allowed_parents = [id_ for sublist in provider.subjects_acceptable for id_ in sublist[0]]
            allows_children = [subs[0][-1] for subs in provider.subjects_acceptable if subs[1]]
            return [sub for sub in Subject.find(Q('parents___id', 'eq', parent)) if provider.subjects_acceptable == [] or self.is_valid_subject(allows_children=allows_children, allowed_parents=allowed_parents, sub=sub)]
        return provider.all_subjects


class PreprintProviderLicenseList(LicenseList):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Preprint_Providers_preprint_provider_licenses_list)
    """
    ordering = ()
    view_category = 'preprint_providers'

    def get_queryset(self):
        provider = PreprintProvider.load(self.kwargs['provider_id'])
        return provider.licenses_acceptable.get_queryset() if provider.licenses_acceptable.count() else super(PreprintProviderLicenseList, self).get_queryset()
