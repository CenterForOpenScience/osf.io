from django import http
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from framework.guid.model import Guid
from api.base.exceptions import NotImplementedError


class GuidRedirect(APIView):

    view_name = 'guid-detail'

    def get(self, request, **kwargs):
        url = self.get_redirect_url(**kwargs)
        if url:
            return http.HttpResponseRedirect(url)
        raise NotFound

    def get_redirect_url(self, **kwargs):
        guid = Guid.load(kwargs['guid'])
        if guid:
            referent = guid.referent
            if getattr(referent, 'absolute_api_v2_url', None):
                return referent.absolute_api_v2_url
            else:
                raise NotImplementedError()
        return None
