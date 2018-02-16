from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from framework.auth.oauth_scopes import CoreScopes

from osf.models import NodeLog
from api.logs.permissions import (
    ContributorOrPublicForLogs
)

from api.base import permissions as base_permissions
from api.logs.serializers import NodeLogSerializer
from api.base.views import JSONAPIBaseView


class LogMixin(object):
    """
    Mixin with convenience method get_log
    """

    def get_log(self):
        log = NodeLog.load(self.kwargs.get('log_id'))
        if not log:
            raise NotFound(
                detail='No log matching that log_id could be found.'
            )

        self.check_object_permissions(self.request, log)
        return log


class NodeLogDetail(JSONAPIBaseView, generics.RetrieveAPIView, LogMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/logs_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublicForLogs
    )

    required_read_scopes = [CoreScopes.NODE_LOG_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeLogSerializer
    view_category = 'logs'
    view_name = 'log-detail'

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        log = self.get_log()
        return log

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        pass
