import json
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response

from osf.models import Guid
from rest_framework.views import APIView

from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder
from api.base.parsers import HMACSignedParser
from api.wb.serializers import (
    WaterbutlerMetadataSerializer,
)
from django.views.decorators.csrf import csrf_exempt


class IACallbackView(APIView):
    """
    This is the callback Pigeon makes that signals IA has finished an archive job.
    """
    view_category = 'ia'
    view_name = 'ia_callback'
    target_lookup_url_kwarg = 'target_id'

    def get_object(self):
        return self.get_target(self.kwargs[self.target_lookup_url_kwarg])

    def get_target(self, target_id):
        guid = Guid.load(target_id)
        if not guid:
            raise NotFound
        target = guid.referent
        return target

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        registration = self.get_object()
        print(registration)
        print(request.__dict__)
        ia_url = json.loads(request._request._body.decode())['ia_url']
        print(ia_url)
        registration.IA_url = ia_url
        registration.save()

