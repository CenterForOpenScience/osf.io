import furl
from django import http
from rest_framework.exceptions import NotFound
from rest_framework import permissions as drf_permissions
from rest_framework import generics

from framework.guid.model import Guid
from framework.auth.oauth_scopes import CoreScopes
from api.base.exceptions import EndpointNotImplementedError
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error, is_truthy
from api.guids.serializers import GuidSerializer


class GuidDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """Find an item by its guid.

    This endpoint will redirect you to the most appropriate URL given an OSF GUID. For example, /v2/guids/{node_id},
    will redirect to /v2/nodes/{node_id} while /v2/guids/{user_id} will redirect to /v2/users/{user_id}. If the GUID
    does not resolve, you will receive a 410 GONE response. If the GUID corresponds to an item that does not have a
    corresponding endpoint (e.g. wiki pages), you will receive a 501 NOT_IMPLEMENTED response.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.GUIDS_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'guids'
    view_name = 'guid-detail'

    serializer_class = GuidSerializer

    @staticmethod
    def should_resolve(request):
        resolve = request.query_params.get('resolve')
        return resolve is None or is_truthy(resolve)

    def get_serializer_class(self):
        if not self.should_resolve(self.request):
            return self.serializer_class
        return None

    def get_object(self):
        return get_object_or_error(
            Guid,
            self.kwargs['guids'],
            display_name='guid'
        )

    def get(self, request, **kwargs):
        if not self.should_resolve(self.request):
            return super(GuidDetail, self).get(request, **kwargs)

        url = self.get_redirect_url(**kwargs)
        if url:
            if self.request.query_params:
                url = furl.furl(url).add(query_params=self.request.query_params).url
            return http.HttpResponseRedirect(url)
        raise NotFound

    def get_redirect_url(self, **kwargs):
        guid = Guid.load(kwargs['guids'])
        if guid:
            referent = guid.referent
            if getattr(referent, 'absolute_api_v2_url', None):
                return referent.absolute_api_v2_url
            else:
                raise EndpointNotImplementedError()
        return None
