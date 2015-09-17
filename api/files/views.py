from rest_framework import generics
from rest_framework import permissions as drf_permissions

from website.files.models import FileNode
from website.files.models import FileVersion

from api.base.permissions import PermissionWithGetter
from api.base.utils import get_object_or_error
from api.nodes.permissions import ContributorOrPublic
from api.nodes.permissions import ReadOnlyIfRegistration
from api.files.permissions import CheckedOutOrAdmin
from api.files.serializers import FileSerializer
from api.files.serializers import FileVersionSerializer


class FileMixin(object):
    """Mixin with convenience methods for retrieving the current file based on the
    current URL. By default, fetches the file based on the file_id kwarg.
    """

    serializer_class = FileSerializer
    file_lookup_url_kwarg = 'file_id'

    def get_file(self, check_permissions=True):
        obj = get_object_or_error(FileNode, self.kwargs[self.file_lookup_url_kwarg])

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        return obj.wrapped()


class FileDetail(generics.RetrieveUpdateAPIView, FileMixin):
    """Details about a specific file.
    """
    serializer_class = FileSerializer
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CheckedOutOrAdmin,
        PermissionWithGetter(ContributorOrPublic, 'node'),
        PermissionWithGetter(ReadOnlyIfRegistration, 'node'),
    )

    def get_node(self):
        return self.get_file().node

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_file()


class FileVersionsList(generics.ListAPIView, FileMixin):
    """Details about a specific file.
    """
    serializer_class = FileVersionSerializer
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        PermissionWithGetter(ContributorOrPublic, 'node'),
    )

    def get_queryset(self):
        return self.get_file().versions


def node_from_version(request, view, obj):
    return view.get_file(check_permissions=False).node


class FileVersionDetail(generics.RetrieveAPIView, FileMixin):

    serializer_class = FileVersionSerializer
    version_lookup_url_kwarg = 'version_id'
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        PermissionWithGetter(ContributorOrPublic, node_from_version)
    )

    # overrides RetrieveAPIView
    def get_object(self):
        file = self.get_file()
        maybe_version = file.get_version(self.kwargs[self.version_lookup_url_kwarg])

        # May raise a permission denied
        # Kinda hacky but versions have no reference to node or file
        self.check_object_permissions(self.request, file)
        return get_object_or_error(FileVersion, getattr(maybe_version, '_id', ''))
