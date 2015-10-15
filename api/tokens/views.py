"""
Views related to person access tokens. Intended for OSF internal use only
"""
from rest_framework.exceptions import APIException
from rest_framework import generics
from rest_framework import renderers
from rest_framework import permissions as drf_permissions

from modularodm import Q

from framework.auth import cas
from framework.auth.oauth_scopes import CoreScopes

from api.base.filters import ODMFilterMixin
from api.base.utils import get_object_or_error
from api.base import permissions as base_permissions
from api.tokens.permissions import OwnerOnly
from api.tokens.models import ApiOAuth2PersonalToken
from api.tokens.serializers import ApiOAuth2PersonalTokenSerializer


class TokenList(generics.ListCreateAPIView, ODMFilterMixin):
    """
    Get a list of personal access tokens that the user has registered
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        OwnerOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.APPLICATIONS_READ]
    required_write_scopes = [CoreScopes.APPLICATIONS_WRITE]

    serializer_class = ApiOAuth2PersonalTokenSerializer

    renderer_classes = [renderers.JSONRenderer]  # Hide from web-browsable API tool

    def get_default_odm_query(self):

        user_id = self.request.user._id
        return (
            Q('user_id', 'eq', user_id) &
            Q('is_active', 'eq', True)
        )

    # overrides ListAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return ApiOAuth2PersonalToken.find(query)

    def perform_create(self, serializer):
        """Add user to the created object"""
        serializer.validated_data['user_id'] = self.request.user
        serializer.save()


class TokenDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Get information about a specific personal access token that the user has registered

    Should not return information if the application belongs to a different user
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        OwnerOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.APPLICATIONS_READ]
    required_write_scopes = [CoreScopes.APPLICATIONS_WRITE]

    serializer_class = ApiOAuth2PersonalTokenSerializer

    renderer_classes = [renderers.JSONRenderer]  # Hide from web-browsable API tool

    # overrides RetrieveAPIView
    def get_object(self):
        obj = get_object_or_error(ApiOAuth2PersonalToken,
                                  Q('token_id', 'eq', self.kwargs['token_id']) &
                                  Q('is_active', 'eq', True))

        self.check_object_permissions(self.request, obj)
        return obj

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        """Instance is not actually deleted from DB- just flagged as inactive, which hides it from list views"""
        obj = self.get_object()
        try:
            obj.deactivate(save=True)
        except cas.CasHTTPError:
            raise APIException("Could not revoke  tokens; please try again later")

    def perform_update(self, serializer):
        """Necessary to prevent user_id field from being blanked on updates"""
        serializer.validated_data['user_id'] = self.request.user
        # TODO: Write code to transfer ownership
        serializer.save(owner=self.request.user)
