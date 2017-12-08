from itertools import chain
from waffle.models import Flag, Switch, Sample

from rest_framework import generics
from rest_framework import permissions as drf_permissions

from api.base.views import JSONAPIBaseView
from api.base.filters import ListFilterMixin
from api.waffle.serializers import WaffleSerializer


class WaffleList(JSONAPIBaseView, generics.ListAPIView):
    """
    Test view that returns all flags in db
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    serializer_class = WaffleSerializer
    view_category = 'waffle'
    view_name = 'waffle-list'

    # overrides ListAPIView
    def get_queryset(self):
        query_params = self.request.query_params
        if query_params:
            flags = Flag.objects.filter(name__in=query_params.get('flags', '').split(','))
            switches = Switch.objects.filter(name__in=query_params.get('switches', '').split(','))
            samples = Sample.objects.filter(name__in=query_params.get('samples', '').split(','))
            return list(chain(flags, switches, samples))
        else:
            return list(chain(Flag.objects.all(), Switch.objects.all(), Sample.objects.all()))
