import furl
from django import http
from django.core.urlresolvers import resolve
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
        """
        If the ?resolve query param is present, this view will return a simple payload containing a relationship link
        to the final endpoint, instead of redirecting to the final destination API URL for that resource type.
        """
        query_params = getattr(request, 'query_params', request.GET)
        flag = query_params.get('resolve')
        return flag is None or is_truthy(resolve)

    @staticmethod
    def should_resolve_payload(request):
        """
        If the ?payload query param is present (at all, with any value), this view will return the full payload
            expected for that resource type

        In order to use this endpoint, a user must have appropriate permissions (access to the resource, and, if using
        OAuth, a token with the appropriate scopes)
        """
        query_params = getattr(request, 'query_params', request.GET)
        # Just check that any value is present. If the query param is present w/o value, this will be an empty string.
        flag = query_params.get('payload', None)
        return flag is not None

    def get_serializer_class(self):
        if not self.should_resolve(self.request):
            return self.serializer_class
        return None

    def get_object(self):
        return get_object_or_error(
            Guid,
            self.kwargs['guids'],
            display_name='guid',
            prefetch_fields=self.serializer_class().model_field_names
        )

    def get(self, request, **kwargs):
        # Three behaviors (old /?resolve may be deprecated/legacy behavior)
        if self.should_resolve_payload(request):
            # URL ?payload: return the payload of the final response for this single resource
            url = self.get_redirect_url(absolute=False, **kwargs)
            dest = resolve(url)
            view = dest.func
            return view(request._request, *dest.args, **dest.kwargs)

        if not self.should_resolve(self.request):
            # URL ?resolve: return a simple payload linking to the authoritative url
            return super(GuidDetail, self).get(request, **kwargs)

        # Else return a 301 that redirects the client to the final authoritative URL
        url = self.get_redirect_url(absolute=True, **kwargs)
        if url:
            query_params = getattr(request, 'query_params', request.GET)
            if query_params:
                url = furl.furl(url).add(query_params=self.request.query_params).url
            return http.HttpResponseRedirect(url)
        raise NotFound

    def get_redirect_url(self, absolute=True, **kwargs):
        guid = Guid.load(kwargs['guids'])
        url_property = 'absolute_api_v2_url' if absolute else 'deep_api_v2_url'
        if guid:
            referent = guid.referent
            url = getattr(referent, url_property, None)
            if url:
                return url
            else:
                raise EndpointNotImplementedError
        return None
