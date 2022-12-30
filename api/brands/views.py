from django.core.exceptions import ObjectDoesNotExist
from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound

from framework.auth.oauth_scopes import CoreScopes
from osf.models import Brand
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.brands.serializers import BrandSerializer


class BrandMixin(object):
    """Mixin with convenience method get_brand
    """

    brand_lookup_url_kwarg = 'brand_id'

    def get_brand(self):
        brand_id = self.kwargs[self.brand_lookup_url_kwarg]

        # This conditional intended to be temporary until we can address issues that are causing brand_id to be
        # stringified IRL but not in the test app. Remove this comment if test app does no longer gives false positive
        # for this function when registration provider with `.brand is None` is embedded or issue is conclusively fixed.
        if self.kwargs.get('is_embedded') and brand_id == 'None':
            raise NotFound

        try:
            inst = Brand.objects.get(id=int(brand_id))
        except ObjectDoesNotExist:
            raise NotFound

        return inst


class BrandList(JSONAPIBaseView, generics.ListAPIView, BrandMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/institutions_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Brand

    serializer_class = BrandSerializer
    view_category = 'brands'
    view_name = 'brand-list'

    ordering = ('name', )

    # overrides ListAPIView
    def get_queryset(self):
        return Brand.objects.filter()


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
