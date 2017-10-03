from rest_framework import generics
from rest_framework import permissions as drf_permissions

from osf.models import AbstractNode
from api.base.views import JSONAPIBaseView

from api.osfstorage.serializers import OsfStorageSerializer


class OsfStorageList(JSONAPIBaseView, generics.CreateAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        # base_permissions.TokenHasScope,
    )

    serializer_class = OsfStorageSerializer
    view_category = 'osfstorage'
    view_name = 'osfstorage-list'


    def get_default_queryset(self):
        return PreprintProvider.objects.all()

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()
