from django import http
from rest_framework.exceptions import NotFound
from rest_framework import permissions as drf_permissions

from framework.guid.model import Guid
from framework.auth.oauth_scopes import CoreScopes, ComposedScopes
from api.base.exceptions import EndpointNotImplementedError
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView


class GuidRedirect(JSONAPIBaseView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [ComposedScopes.FULL_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'guids'
    view_name = 'guid-detail'

    def get(self, request, **kwargs):
        url = self.get_redirect_url(**kwargs)
        if url:
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
