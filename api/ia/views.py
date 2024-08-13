import json
from rest_framework.exceptions import NotFound

from osf.models import Guid
from rest_framework.views import APIView
from django.http import JsonResponse
from api.base import permissions as base_permissions


class IACallbackView(APIView):
    """
    This is the callback Pigeon makes that signals IA has finished an archive job.
    """
    view_category = 'ia'
    view_name = 'ia_callback'
    target_lookup_url_kwarg = 'target_id'
    permission_classes = (
        base_permissions.RequestHasPigeonToken,
    )

    def get_object(self):
        return self.get_target(self.kwargs[self.target_lookup_url_kwarg])

    def get_target(self, target_id):
        guid = Guid.load(target_id)
        if not guid:
            raise NotFound
        target = guid.referent
        return target

    def post(self, request, *args, **kwargs):
        registration = self.get_object()
        ia_url = json.loads(request.body)['ia_url']
        registration.ia_url = ia_url
        registration.save()
        return JsonResponse({'status': 'complete'})
