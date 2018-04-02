from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound

from framework.auth.oauth_scopes import CoreScopes

from osf.models import (
    Guid,
    BaseFileNode,
    FileVersion,
    QuickFilesNode
)

from api.base.exceptions import Gone
from api.base.permissions import PermissionWithGetter
from api.base.throttling import CreateGuidThrottle, NonCookieAuthThrottle, UserRateThrottle
from api.base import utils
from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.nodes.permissions import ContributorOrPublic
from api.nodes.permissions import ReadOnlyIfRegistration
from api.files.permissions import IsPreprintFile
from api.files.permissions import CheckedOutOrAdmin
from api.files.serializers import FileSerializer
from api.files.serializers import FileDetailSerializer, QuickFilesDetailSerializer
from api.files.serializers import FileVersionSerializer


class FileMixin(object):
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
            if obj.is_deleted:
                raise Gone(detail='The requested file is no longer available.')
            if not isinstance(obj, BaseFileNode):
                raise NotFound

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
        PermissionWithGetter(ContributorOrPublic, 'node'),
        PermissionWithGetter(ReadOnlyIfRegistration, 'node'),
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileDetailSerializer
    throttle_classes = (CreateGuidThrottle, NonCookieAuthThrottle, UserRateThrottle, )
    view_category = 'files'
    view_name = 'file-detail'

    def get_serializer_class(self):
        try:
            node = self.get_node()
        except (NotFound, Gone):
            return FileDetailSerializer
        else:
            if isinstance(node, QuickFilesNode):
                return QuickFilesDetailSerializer
            return FileDetailSerializer

    def get_node(self):
        return self.get_file().node

    # overrides RetrieveAPIView
    def get_object(self):
        user = utils.get_user_auth(self.request).user
        file = self.get_file()
        if self.request.GET.get('create_guid', False):
            # allows quickfiles to be given guids when another user wants a permanent link to it
            if (self.get_node().has_permission(user, 'admin') and utils.has_admin_scope(self.request)) or file.node.is_quickfiles:
                file.get_guid(create=True)
        return file


class FileVersionsList(JSONAPIBaseView, generics.ListAPIView, FileMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/files_versions).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, 'node'),
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
    return view.get_file(check_permissions=False).node


class FileVersionDetail(JSONAPIBaseView, generics.RetrieveAPIView, FileMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/files_version_detail).
    """
    version_lookup_url_kwarg = 'version_id'
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, node_from_version)
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
        self.check_object_permissions(self.request, file)
        return utils.get_object_or_error(FileVersion, getattr(maybe_version, '_id', ''), self.request)

    def get_serializer_context(self):
        context = JSONAPIBaseView.get_serializer_context(self)
        context['file'] = self.file
        return context
