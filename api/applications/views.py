"""
Views related to OAuth2 platform applications. Intended for OSF internal use only
"""
from modularodm import Q
from rest_framework import permissions as drf_permissions
from rest_framework import generics
from rest_framework.exceptions import APIException

from api.applications.serializers import (ApiOAuth2ApplicationDetailSerializer,
                                          ApiOAuth2ApplicationResetSerializer,
                                          ApiOAuth2ApplicationSerializer)
from api.base import permissions as base_permissions
from api.base.filters import ODMFilterMixin
from api.base.renderers import JSONAPIRenderer, JSONRendererWithESISupport
from api.base.utils import get_object_or_error
from api.base.views import JSONAPIBaseView
from framework.auth import cas
from framework.auth.oauth_scopes import CoreScopes
from website.models import ApiOAuth2Application


class ApplicationMixin(object):
    """Mixin with convenience methods for retrieving the current application based on the
    current URL. By default, fetches the current application based on the client_id kwarg.
    """

    def get_app(self):
        app = get_object_or_error(
            ApiOAuth2Application,
            Q('client_id', 'eq', self.kwargs['client_id'])
            & Q('is_active', 'eq', True))

        self.check_object_permissions(self.request, app)
        return app


class ApplicationList(JSONAPIBaseView, generics.ListCreateAPIView,
                      ODMFilterMixin):
    """
    Get a list of API applications (eg OAuth2) that the user has registered
    """
    permission_classes = (drf_permissions.IsAuthenticated,
                          base_permissions.OwnerOnly,
                          base_permissions.TokenHasScope, )

    required_read_scopes = [CoreScopes.APPLICATIONS_READ]
    required_write_scopes = [CoreScopes.APPLICATIONS_WRITE]

    serializer_class = ApiOAuth2ApplicationSerializer
    view_category = 'applications'
    view_name = 'application-list'

    # TODO: When we switch to Swagger this should be removed in lieu of a better
    # solution for hiding this api endpoint
    renderer_classes = [JSONRendererWithESISupport,
                        JSONAPIRenderer, ]  # Hide from web-browsable API tool

    def get_default_odm_query(self):

        user_id = self.request.user._id
        return (Q('owner', 'eq', user_id) & Q('is_active', 'eq', True))

    # overrides ListAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return ApiOAuth2Application.find(query)

    def perform_create(self, serializer):
        """Add user to the created object"""
        serializer.validated_data['owner'] = self.request.user
        serializer.save()


class ApplicationDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView,
                        ApplicationMixin):
    """
    Get information about a specific API application (eg OAuth2) that the user has registered

    Should not return information if the application belongs to a different user
    """
    permission_classes = (drf_permissions.IsAuthenticated,
                          base_permissions.OwnerOnly,
                          base_permissions.TokenHasScope, )

    required_read_scopes = [CoreScopes.APPLICATIONS_READ]
    required_write_scopes = [CoreScopes.APPLICATIONS_WRITE]

    serializer_class = ApiOAuth2ApplicationDetailSerializer
    view_category = 'applications'
    view_name = 'application-detail'

    # TODO: When we switch to Swagger this should be removed in lieu of a better
    # solution for hiding this api endpoint
    renderer_classes = [JSONRendererWithESISupport,
                        JSONAPIRenderer, ]  # Hide from web-browsable API tool

    def get_object(self):
        return self.get_app()

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        """Instance is not actually deleted from DB- just flagged as inactive, which hides it from list views"""
        obj = self.get_object()
        try:
            obj.deactivate(save=True)
        except cas.CasHTTPError:
            raise APIException(
                "Could not revoke application auth tokens; please try again later")

    def perform_update(self, serializer):
        """Necessary to prevent owner field from being blanked on updates"""
        serializer.validated_data['owner'] = self.request.user
        # TODO: Write code to transfer ownership
        serializer.save(owner=self.request.user)


class ApplicationReset(JSONAPIBaseView, generics.CreateAPIView,
                       ApplicationMixin):
    """
    Resets client secret of a specific API application (eg OAuth2) that the user has registered

    Should not perform update or return information if the application belongs to a different user
    """
    permission_classes = (drf_permissions.IsAuthenticated,
                          base_permissions.OwnerOnly,
                          base_permissions.TokenHasScope, )

    required_read_scopes = [CoreScopes.APPLICATIONS_READ]
    required_write_scopes = [CoreScopes.APPLICATIONS_WRITE]

    serializer_class = ApiOAuth2ApplicationResetSerializer

    # TODO: When we switch to Swagger this should be removed in lieu of a better
    # solution for hiding this api endpoint
    renderer_classes = [JSONRendererWithESISupport,
                        JSONAPIRenderer, ]  # Hide from web-browsable API tool

    view_category = 'applications'
    view_name = 'application-reset'

    def get_object(self):
        return self.get_app()

    def perform_create(self, serializer):
        """Resets the application client secret, revokes all tokens"""
        app = self.get_object()
        app.reset_secret(save=True)
        app.reload()
        serializer.validated_data['client_secret'] = app.client_secret
