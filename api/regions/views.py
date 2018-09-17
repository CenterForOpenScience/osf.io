from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.filters import ListFilterMixin
from api.base.pagination import MaxSizePagination
from framework.auth.oauth_scopes import CoreScopes
from api.regions.serializers import RegionSerializer

from addons.osfstorage.models import Region
from osf.models import Node


class RegionMixin(object):
    """Mixin with convenience method get_region
    """

    serializer_class = RegionSerializer
    region_lookup_url_kwarg = 'region_id'

    def get_region(self):
        region_id = self.kwargs[self.region_lookup_url_kwarg]
        if self.kwargs.get('is_embedded') is True:
            node_id, node = self.request.parents[Node].items()[0]
            try:
                # use the annotated value if possible
                region_id = node.region
            except AttributeError:
                # use computed property if region annotation does not exist
                # i.e. after creating a node
                region_id = node.osfstorage_region._id
        try:
            reg = Region.objects.get(_id=region_id)
        except Region.DoesNotExist:
            raise NotFound(
                detail='No region matching that region_id could be found.'
            )
        self.check_object_permissions(self.request, reg)
        return reg


class RegionList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    """Undocumented endpoint. Subject to change.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    pagination_class = MaxSizePagination
    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Region

    serializer_class = RegionSerializer
    view_category = 'regions'
    view_name = 'region-list'

    ordering = ('name', )

    def get_default_queryset(self):
        return Region.objects.all()

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class RegionDetail(JSONAPIBaseView, generics.RetrieveAPIView, RegionMixin):
    """Undocumented endpoint. Subject to change.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Region

    serializer_class = RegionSerializer
    view_category = 'regions'
    view_name = 'region-detail'

    ordering = ('name', )

    def get_object(self):
        return self.get_region()
