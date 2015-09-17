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
    """File and folder details.

    Both files and folders are accessed through this endpoint and may be distinguished by the `kind` attribute. `size`
    will be `null` for folders.

    ##Actions

    The `links` property of the response provides endpoints for common file operations. The currently-supported actions
    are:

    ###Get Info (*files, folders*)

        GET /v2/files/55ea00a9cfe1915f0e57d67d/

    The details of a particular file can be retreived by performing a GET request against the url in the `info` property.

    ###Download (*files*)

    To download a file, issue a GET request against the url in the `download` property.  The response will have the
    Content-Disposition header set, which will will trigger a download in a browser.

    ###Create Subfolder (*folders*)

    You can create a subfolder of an existing folder by issuing a PUT request against the `new_folder` url.  The name of
    the new subfolder should be provided in the `name` query parameter.

    ###Upload New File (*folders*)

    To upload a file to a folder, issue a PUT request to the folder's `upload` url with the raw file data in the request
    body, and the `kind` and `name` query parameters set to `'file'` and the desired name of the file.

    ###Update Existing File (*file*)

    To update an existing file, issue a PUT request to the file's `upload` url with the raw file data in the request
    body, and the `kind` and `name` query parameters set to `'file'` and the desired name of the file.

    ###Rename (*files, folders*)

    To rename a file or folder, issue a POST request to the `move` url with the `action` body parameter set to
    `'rename'` and the `rename` body parameter set to the desired name.

    ###Move & Copy (*files, folders*)

    Move and copy actions both use the same request structure, with different values for the `action` body parameters.
    The `path` parameter is also required and should be the `path` attribute of the folder being written to.  The
    `rename` and `conflict` parameters are optional.  If you wish to change the file's or folder's name at its
    destination, set the `rename` parameter to the new name.  The `conflict` param governs how name clashes are
    resolved.  Possible values are `replace` and `keep`.  `replace` is the default and will overwrite the file that
    already exists in the target folder.  `keep` will attempt to keep both by adding a suffix to the new file's name
    until to conflict exists.  The suffix will be ' (**x**)' where **x** is a increasing integer starting from 1.

    ###Delete (*file, folders*)

    To delete a file, send a DELETE request to the `download` url for files, or the `upload` url for folders.

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
