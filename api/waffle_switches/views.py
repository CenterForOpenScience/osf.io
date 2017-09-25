from waffle.models import Switch

from rest_framework import generics
from rest_framework import permissions as drf_permissions

from api.base.views import JSONAPIBaseView
from api.waffle_switches.serializers import WaffleSwitchSerializer


class WaffleSwitchList(JSONAPIBaseView, generics.ListAPIView):
    """
    Test view that returns all switches in db
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    model_class = Switch

    serializer_class = WaffleSwitchSerializer
    view_category = 'waffle-switches'
    view_name = 'waffle-switch-list'

    # overrides ListAPIView
    def get_queryset(self):
        return Switch.objects.all()
