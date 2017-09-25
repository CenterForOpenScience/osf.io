from waffle.models import Flag

from rest_framework import generics
from rest_framework import permissions as drf_permissions

from api.base.views import JSONAPIBaseView
from api.waffle_flags.serializers import WaffleFlagSerializer


class WaffleFlagList(JSONAPIBaseView, generics.ListAPIView):
    """
    Test view that returns all flags in db
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    model_class = Flag

    serializer_class = WaffleFlagSerializer
    view_category = 'waffle-flags'
    view_name = 'waffle-flag-list'

    # overrides ListAPIView
    def get_queryset(self):
        return Flag.objects.all()


class WaffleFlagDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """
    Test view that returns specific flag in db
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    model_class = Flag
    lookup_field = 'name'
    serializer_class = WaffleFlagSerializer
    view_category = 'waffle-flags'
    view_name = 'waffle-flag-detail'

    # overrides RetrieveAPIView
    def get_queryset(self):
        return Flag.objects.all()
