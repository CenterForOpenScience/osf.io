from rest_framework import generics
from rest_framework import permissions as drf_permissions

from website.files.models import File
from website.files.models import FileNode
from website.files.models import FileVersion

from api.base.filters import ODMFilterMixin
from api.base.utils import get_object_or_error
from api.files.permissions import CheckedOutOrAdmin
from api.files.permissions import ContributorOrPublic
from api.files.permissions import ReadOnlyIfRegistration
from api.files.serializers import FileSerializer
from api.files.serializers import FileVersionSerializer


class FileMixin(object):
    """Mixin with convenience methods for retrieving the current file based on the
    current URL. By default, fetches the file based on the file_id kwarg.
    """

    serializer_class = FileSerializer
    file_lookup_url_kwarg = 'file_id'

    def get_file(self, check_permissions=True):
        key = self.kwargs[self.file_lookup_url_kwarg]

        obj = get_object_or_error(FileNode, key)

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        return obj


class FileList(generics.ListAPIView, ODMFilterMixin):
    """Files that the OSF has metadata about

    You can filter on users by their id, name, path, provider
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
    )
    serializer_class = FileSerializer
    ordering = ('-last_touched', )

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return File._filter()

    # overrides ListAPIView
    def get_queryset(self):
        # TODO: sort
        query = self.get_query_from_request()
        return FileNode.find(query)


class FileDetail(generics.RetrieveUpdateAPIView, FileMixin):
    """Details about a specific file.
    """
    serializer_class = FileSerializer
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        CheckedOutOrAdmin,
        ReadOnlyIfRegistration,
    )

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_file()


class FileVersionsList(generics.ListAPIView, FileMixin):
    """Details about a specific file.
    """
    serializer_class = FileVersionSerializer
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
    )

    def get_queryset(self):
        return self.get_file().versions


class FileVersionDetail(generics.RetrieveAPIView, FileMixin):

    serializer_class = FileVersionSerializer
    version_lookup_url_kwarg = 'version_id'
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
    )

    # overrides RetrieveAPIView
    def get_object(self):
        version = get_object_or_error(FileVersion, self.kwargs[self.version_lookup_url_kwarg])
        # May raise a permission denied
        self.check_object_permissions(self.request, version)
        return version
