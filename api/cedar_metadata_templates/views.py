from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound

from api.base import permissions as base_permissions
from api.base.filters import ListFilterMixin
from api.base.versioning import PrivateVersioning
from api.base.views import JSONAPIBaseView
from api.cedar_metadata_templates.serializers import CedarMetadataTemplateSerializer
from framework.auth.oauth_scopes import CoreScopes
from osf.models import CedarMetadataTemplate


class CedarMetadataTemplateList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.CEDAR_METADATA_RECORD_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = CedarMetadataTemplateSerializer
    model_class = CedarMetadataTemplate

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'cedar-metadata-templates'
    view_name = 'cedar-metadata-template-list'

    def get_default_queryset(self):
        return CedarMetadataTemplate.objects.filter(active=True)

    def get_queryset(self):
        return self.get_queryset_from_request()


class CedarMetadataTemplateDetail(JSONAPIBaseView, generics.RetrieveAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = CedarMetadataTemplateSerializer

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'cedar-metadata-templates'
    view_name = 'cedar-metadata-template-detail'

    def get_object(self):
        try:
            return CedarMetadataTemplate.objects.get(_id=self.kwargs['template_id'])
        except CedarMetadataTemplate.DoesNotExist:
            raise NotFound
