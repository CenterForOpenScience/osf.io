from api.base.utils import get_object_or_error
from django.db.models import Q
from django.utils import timezone
from api.base.views import JSONAPIBaseView
from api.banners.serializers import BannerSerializer
from rest_framework import generics
from osf.models import ScheduledBanner
from rest_framework.exceptions import NotFound

class CurrentBanner(JSONAPIBaseView, generics.RetrieveAPIView):

    serializer_class = BannerSerializer
    view_category = 'banners'
    view_name = 'banner-current'

    def get_object(self):
        try:
            return get_object_or_error(ScheduledBanner, Q(start_date__lte=timezone.now(), end_date__gte=timezone.now()), self.request)
        except NotFound:
            return ScheduledBanner()
