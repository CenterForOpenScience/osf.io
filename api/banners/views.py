from osf.models import ScheduledBanner
from osf.utils.storage import BannerImage

from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.banners.serializers import BannerSerializer
from api.base import permissions as base_permissions

from rest_framework import generics
from rest_framework import permissions
from rest_framework.exceptions import NotFound
from framework.auth.oauth_scopes import CoreScopes

from django.db.models import Q
from django.utils import timezone
from django.http import FileResponse
from django.core.files.base import ContentFile


class CurrentBanner(JSONAPIBaseView, generics.RetrieveAPIView):

    serializer_class = BannerSerializer
    # This view goes under the _/ namespace
    versioning_class = None
    view_category = 'banners'
    view_name = 'current'

    permission_classes = (
        base_permissions.TokenHasScope,
        permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    def get_object(self):
        try:
            return get_object_or_error(ScheduledBanner, Q(start_date__lte=timezone.now(), end_date__gte=timezone.now()), self.request)
        except NotFound:
            return ScheduledBanner()


class BannerMedia(JSONAPIBaseView):

    serializer_class = BannerSerializer
    # This view goes under the _/ namespace
    versioning_class = None
    view_category = 'banners'
    view_name = 'media'

    permission_classes = (
        base_permissions.TokenHasScope,
        permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    def get_object(self):
        return get_object_or_error(BannerImage, Q(filename=self.kwargs.get('filename')), self.request)

    def get(self, request, *args, **kwargs):
        response = FileResponse(ContentFile(self.get_object().image))
        response['Content-Type'] = 'image/svg+xml'
        return response
