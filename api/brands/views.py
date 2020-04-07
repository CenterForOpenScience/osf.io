
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound

from framework.auth.oauth_scopes import CoreScopes
from osf.models import Brand
from api.base import permissions as base_permissions
from api.base.pagination import MaxSizePagination
from api.base.filters import ListFilterMixin
from api.base.views import JSONAPIBaseView
from api.brands.serializers import BrandSerializer


class BrandMixin(object):
    """Mixin with convenience method get_brand
    """

    brand_lookup_url_kwarg = 'brand_id'

    def get_brand(self):
        brand_id = self.kwargs[self.brand_lookup_url_kwarg]

        try:
            inst = Brand.objects.get(id=int(brand_id))
        except ObjectDoesNotExist:
            raise NotFound

        return inst


class BrandList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, BrandMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/institutions_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Brand

    pagination_class = MaxSizePagination
    serializer_class = BrandSerializer
    view_category = 'brands'
    view_name = 'brand-list'

    ordering = ('name', )

    def get_default_queryset(self):
        return Brand.objects.filter()

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class BrandDetail(JSONAPIBaseView, generics.RetrieveAPIView, BrandMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/subjects_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = BrandSerializer

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'brands'
    view_name = 'brand-detail'

    def get_object(self):
        return self.get_brand()
