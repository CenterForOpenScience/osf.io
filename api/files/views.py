from django.db.models import Max

from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound

from framework.auth.oauth_scopes import CoreScopes

from osf.models import (
    Guid,
    BaseFileNode,
    FileVersion,
    CedarMetadataRecord,
)

from api.base.exceptions import Gone
from api.base.filters import ListFilterMixin
from api.base.permissions import PermissionWithGetter
from api.base.throttling import CreateGuidThrottle, NonCookieAuthThrottle, UserRateThrottle, BurstRateThrottle
from api.base import utils
from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.cedar_metadata_records.serializers import CedarMetadataRecordsListSerializer
from api.cedar_metadata_records.utils import can_view_record
from api.nodes.permissions import ContributorOrPublic
from api.files import annotations
from api.files.permissions import IsPreprintFile
from api.files.permissions import CheckedOutOrAdmin
from api.files.serializers import FileSerializer
from api.files.serializers import FileDetailSerializer
from api.files.serializers import FileVersionSerializer
from osf.utils.permissions import ADMIN


class FileMixin:
    """Mixin with convenience methods for retrieving the current file based on the
    current URL. By default, fetches the file based on the file_id kwarg.
    """

    serializer_class = FileSerializer
    file_lookup_url_kwarg = 'file_id'

    def get_file(self, check_permissions=True):
        try:
            obj = utils.get_object_or_error(BaseFileNode, self.kwargs[self.file_lookup_url_kwarg], self.request, display_name='file')
        except NotFound:
            obj = utils.get_object_or_error(Guid, self.kwargs[self.file_lookup_url_kwarg], self.request).referent
            if not isinstance(obj, BaseFileNode):
                raise NotFound
            if obj.is_deleted:
                raise Gone(detail='The requested file is no longer available.')

        if getattr(obj.target, 'deleted', None):
            raise Gone(detail='The requested file is no longer available')

        if getattr(obj.target, 'is_quickfiles', False) and getattr(obj.target, 'creator'):
            if obj.target.creator.is_disabled:
                raise Gone(detail='This user has been deactivated and their quickfiles are no longer available.')

        if getattr(obj.target, 'is_retracted', False):
            raise Gone(detail='The requested file is no longer available.')

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        return obj


class FileDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, FileMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/files_detail).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        IsPreprintFile,
        CheckedOutOrAdmin,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, 'target'),
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileDetailSerializer
    throttle_classes = (CreateGuidThrottle, NonCookieAuthThrottle, UserRateThrottle, BurstRateThrottle)
    view_category = 'files'
    view_name = 'file-detail'

    def get_serializer_class(self):
        return FileDetailSerializer

    def get_target(self):
        return self.get_file().target

    # overrides RetrieveAPIView
    def get_object(self):
        user = utils.get_user_auth(self.request).user
        file = self.get_file()

        if self.request.GET.get('create_guid', False):
            # allows quickfiles to be given guids when another user wants a permanent link to it
            if (self.get_target().has_permission(user, ADMIN) and utils.has_admin_scope(self.request)) or getattr(file.target, 'is_quickfiles', False):
                file.get_guid(create=True)

        # We normally would pass this through `get_file` as an annotation, but the `select_for_update` feature prevents
        # grouping versions in an annotation
        if file.kind == 'file':
            file.show_as_unviewed = annotations.check_show_as_unviewed(
                user=self.request.user, osf_file=file,
            )
            if file.provider == 'osfstorage':
                file.date_modified = file.versions.aggregate(Max('created'))['created__max']
            else:
                file.date_modified = file.history[-1]['modified']

        return file


class FileVersionsList(JSONAPIBaseView, generics.ListAPIView, FileMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/files_versions).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, 'target'),
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileVersionSerializer
    view_category = 'files'
    view_name = 'file-versions'

    ordering = ('-modified',)

    def get_queryset(self):
        self.file = self.get_file()
        return self.file.versions.all()

    def get_serializer_context(self):
        context = JSONAPIBaseView.get_serializer_context(self)
        context['file'] = self.file
        return context


def node_from_version(request, view, obj):
    return view.get_file(check_permissions=False).target


class FileVersionDetail(JSONAPIBaseView, generics.RetrieveAPIView, FileMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/files_version_detail).
    """
    version_lookup_url_kwarg = 'version_id'
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, node_from_version),
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileVersionSerializer
    view_category = 'files'
    view_name = 'version-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        self.file = self.get_file()
        maybe_version = self.file.get_version(self.kwargs[self.version_lookup_url_kwarg])

        # May raise a permission denied
        # Kinda hacky but versions have no reference to node or file
        self.check_object_permissions(self.request, self.file)
        return utils.get_object_or_error(FileVersion, getattr(maybe_version, '_id', ''), self.request)

    def get_serializer_context(self):
        context = JSONAPIBaseView.get_serializer_context(self)
        context['file'] = self.file
        return context


class FileCedarMetadataRecordsList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, FileMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, 'target'),
    )
    required_read_scopes = [CoreScopes.CEDAR_METADATA_RECORD_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = CedarMetadataRecordsListSerializer

    view_category = 'files'
    view_name = 'file-cedar-metadata-records-list'

    def get_default_queryset(self):
        guid = self.get_file().get_guid()
        if not guid:
            return CedarMetadataRecord.objects.none()
        file_records = CedarMetadataRecord.objects.filter(guid___id=guid._id)
        user_auth = utils.get_user_auth(self.request)
        record_ids = [record.id for record in file_records if can_view_record(user_auth, record, guid_type=BaseFileNode)]
        return CedarMetadataRecord.objects.filter(pk__in=record_ids)

    def get_queryset(self):
        return self.get_queryset_from_request()
