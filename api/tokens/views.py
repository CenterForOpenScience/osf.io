"""
Views related to personal access tokens. Intended for OSF internal use only
"""
from rest_framework.exceptions import APIException
from rest_framework import generics
from rest_framework import renderers
from rest_framework import permissions as drf_permissions

from api.base.renderers import JSONAPIRenderer, JSONRendererWithESISupport
from modularodm import Q

from framework.auth import cas
from framework.auth.oauth_scopes import CoreScopes

from api.base.filters import ODMFilterMixin
from api.base.utils import get_object_or_error
from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.tokens.serializers import ApiOAuth2PersonalTokenSerializer

from website.models import ApiOAuth2PersonalToken


class TokenList(JSONAPIBaseView, generics.ListCreateAPIView, ODMFilterMixin):
    """
    Get a list of personal access tokens that the user has registered
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.OwnerOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.TOKENS_READ]
    required_write_scopes = [CoreScopes.TOKENS_WRITE]

    serializer_class = ApiOAuth2PersonalTokenSerializer
    view_category = 'tokens'
    view_name = 'token-list'

    renderer_classes = [JSONRendererWithESISupport, JSONAPIRenderer, ]  # Hide from web-browsable API tool

    def get_default_odm_query(self):

        owner = self.request.user._id
        return (
            Q('owner', 'eq', owner) &
            Q('is_active', 'eq', True)
        )

    # overrides ListAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return ApiOAuth2PersonalToken.find(query)

    def perform_create(self, serializer):
        """Add user to the created object"""
        serializer.validated_data['owner'] = self.request.user
        serializer.save()


class TokenDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    """
    Get information about a specific personal access token that the user has registered

    Should not return information if the token belongs to a different user
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.OwnerOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.TOKENS_READ]
    required_write_scopes = [CoreScopes.TOKENS_WRITE]

    serializer_class = ApiOAuth2PersonalTokenSerializer
    view_category = 'tokens'
    view_name = 'token-detail'

    renderer_classes = [JSONRendererWithESISupport, JSONAPIRenderer, ]  # Hide from web-browsable API tool

    # overrides RetrieveAPIView
    def get_object(self):
        obj = get_object_or_error(ApiOAuth2PersonalToken,
                                  Q('_id', 'eq', self.kwargs['_id']) &
                                  Q('is_active', 'eq', True))

        self.check_object_permissions(self.request, obj)
        return obj

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        """Instance is not actually deleted from DB- just flagged as inactive, which hides it from views"""
        obj = self.get_object()
        try:
            obj.deactivate(save=True)
        except cas.CasHTTPError:
            raise APIException("Could not revoke tokens; please try again later")

    def perform_update(self, serializer):
        """Necessary to prevent owner field from being blanked on updates"""
        serializer.validated_data['owner'] = self.request.user
        serializer.save(owner=self.request.user)
