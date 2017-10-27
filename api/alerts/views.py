from django.db.models import Q
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from framework.auth.oauth_scopes import CoreScopes

from api.base.filters import ListFilterMixin
from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error, get_user_auth
from api.base.views import JSONAPIBaseView
from api.alerts.serializers import AlertSerializer

from osf.models import DismissedAlert


class DismissedAlertDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALERTS_READ]
    required_write_scopes = [CoreScopes.ALERTS_WRITE]
    model_class = DismissedAlert

    serializer_class = AlertSerializer
    view_category = 'alerts'
    view_name = 'alerts-detail'

    ordering = ('-created',)

    # overrides RetrieveAPIView
    def get_object(self):
        try:
            obj = get_object_or_error(DismissedAlert, Q(_id=self.kwargs['_id']), self.request)
        except DismissedAlert.DoesNotExist:
            raise NotFound
        return obj


class DismissedAlertList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin):
    """List of Dismissed Alerts.
    ###Creating New Dismissed Alert

        Method:        POST
        URL:           /alerts/
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "alerts",             # required
                           "id":   {id},                 # required
                           "attributes": {
                             "location":     {location}, # required
                           }
                         }
                       }
        Success:       201 CREATED + alert representation
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALERTS_READ]
    required_write_scopes = [CoreScopes.ALERTS_WRITE]
    model_class = DismissedAlert

    serializer_class = AlertSerializer
    view_category = 'alerts'
    view_name = 'alerts-list'

    def get_default_queryset(self):
        return DismissedAlert.objects.filter(user=self.request.user)

    def get_queryset(self):
        return self.get_queryset_from_request()

    def perform_create(self, serializer):
        """Add user to the created alert"""
        user = get_user_auth(self.request).user
        serializer.validated_data['user'] = user
        serializer.save()
