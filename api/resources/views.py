import logging

from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from api.base import permissions as base_permissions
from api.base.exceptions import EnumFieldMemberError, JSONAPIException
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.views import JSONAPIBaseView
from api.resources.permissions import (
    ResourceDetailPermission,
    ResourceListPermission,
)
from api.resources.serializers import ResourceSerializer
from framework.auth.oauth_scopes import CoreScopes
from osf.models import Guid, OutcomeArtifact, Registration

logger = logging.getLogger(__name__)


class ResourceList(JSONAPIBaseView, generics.ListCreateAPIView):
    permission_classes = (
        ResourceListPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_REGISTRATION_RESOURCES]
    required_write_scopes = [CoreScopes.WRITE_REGISTRATION_RESOURCES]

    view_category = "resources"
    view_name = "resource-list"

    serializer_class = ResourceSerializer

    parser_classes = (
        JSONAPIMultipleRelationshipsParser,
        JSONAPIMultipleRelationshipsParserForRegularJSON,
    )

    def get_permissions_proxy(self):
        try:
            registration_guid = self.request.data["registration"]
        except KeyError:
            raise JSONAPIException(
                detail='Must provide "registration" relationship in payload"',
                source={"pointer": "/data/relationships/registration/data/id"},
            )

        registration = Registration.load(registration_guid)
        if not registration:
            raise NotFound
        return registration


class ResourceDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        ResourceDetailPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_REGISTRATION_RESOURCES]
    required_write_scopes = [CoreScopes.WRITE_REGISTRATION_RESOURCES]

    view_category = "resources"
    view_name = "resource-detail"

    serializer_class = ResourceSerializer

    parser_classes = (
        JSONAPIMultipleRelationshipsParser,
        JSONAPIMultipleRelationshipsParserForRegularJSON,
    )

    def get_object(self):
        try:
            return OutcomeArtifact.objects.get(_id=self.kwargs["resource_id"])
        except OutcomeArtifact.DoesNotExist:
            raise NotFound

    def get_permissions_proxy(self):
        return Guid.load(self.get_object().primary_resource_guid).referent

    def patch(self, *args, **kwargs):
        try:
            return super().patch(*args, **kwargs)
        except EnumFieldMemberError as e:
            e.source = {"pointer": "/data/attributes/resource_type"}
            raise e

    def perform_destroy(self, instance):
        instance.delete(api_request=self.request)
