from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound

from framework.auth.oauth_scopes import CoreScopes

from osf.models import (
    Guid,
    FileNode,
    FileVersion,
    StoredFileNode
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
from api.files.serializers import FileDetailSerializer
from api.files.serializers import FileVersionSerializer


class FileMixin(object):
    """Mixin with convenience methods for retrieving the current file based on the
    current URL. By default, fetches the file based on the file_id kwarg.
    """

    serializer_class = FileSerializer
    file_lookup_url_kwarg = 'file_id'

    def get_file(self, check_permissions=True):
        try:
            obj = utils.get_object_or_error(FileNode, self.kwargs[self.file_lookup_url_kwarg], prefetch_fields=self.serializer_class().model_field_names)
        except (NotFound, Gone):
            obj = utils.get_object_or_error(Guid, self.kwargs[self.file_lookup_url_kwarg], prefetch_fields=self.serializer_class().model_field_names).referent
            if not isinstance(obj, StoredFileNode):
                raise NotFound
            obj = obj.wrapped()

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        return obj.wrapped()


class FileDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, FileMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Files_files_detail).
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

    def get_node(self):
        return self.get_file().node

    # overrides RetrieveAPIView
    def get_object(self):
        user = utils.get_user_auth(self.request).user

        if (self.request.GET.get('create_guid', False) and
                self.get_node().has_permission(user, 'admin') and
                utils.has_admin_scope(self.request)):
            self.get_file(check_permissions=True).get_guid(create=True)

        return self.get_file()

class FileVersionsList(JSONAPIBaseView, generics.ListAPIView, FileMixin):
    """List of versions for the requested file. *Read-only*.

    Paginated list of file versions, ordered by the date each version was created/modified.

    <!--- Copied Spiel from FileVersionDetail -->

    A specific version of an uploaded file.  Note that the version is tied to the id/path, so two versions of the same
    file could have completely different contents and formats.  That's on you, though.  Don't do that.

    Unlike the OSF File entity which can represent files and folders, FileVersions only ever represent files. When a
    file is first uploaded to the "osfstorage" provider through the API it is assigned version 1.  Each time it is
    updated through the API, the version number is incremented.  Files stored on other providers will follow that
    provider's versioning semantics.

    ##FileVersion Attributes

    <!--- Copied Attributes from FileVersionDetail -->

    For an OSF FileVersion entity the API `type` is "file_versions".

        name          type     description
        =================================================================================
        size          integer  size of file in bytes
        content_type  string   MIME content-type for the file. May be null if unavailable.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    File versions may be filtered by their `id`, `size`, or `content_type`.

    #This Request/Response

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

    def get_queryset(self):
        return self.get_file().versions.all()


def node_from_version(request, view, obj):
    return view.get_file(check_permissions=False).node


class FileVersionDetail(JSONAPIBaseView, generics.RetrieveAPIView, FileMixin):
    """Details about a specific file version. *Read-only*.

    A specific version of an uploaded file.  Note that the version is tied to the id/path, so two versions of the same
    file could have completely different contents and formats.  That's on you, though.  Don't do that.

    Unlike the OSF File entity which can represent files and folders, FileVersions only ever represent files. When a
    file is first uploaded through the API it is assigned version 1.  Each time it is updated through the API, the
    version number is incremented.

    ##Attributes

    For an OSF FileVersion entity the API `type` is "file_versions".

        name          type     description
        =================================================================================
        size          integer  size of file in bytes
        content_type  string   MIME content-type for the file. May be null if unavailable.

    ##Relationships

    *None*.

    ##Links

        self:  the canonical api endpoint for this version of the file
        html:  the OSF webpage for this file version

    ##Actions

    *None*.

    ##Query Params

    *None*.

    #This Request/Response
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
        file = self.get_file()
        maybe_version = file.get_version(self.kwargs[self.version_lookup_url_kwarg])

        # May raise a permission denied
        # Kinda hacky but versions have no reference to node or file
        self.check_object_permissions(self.request, file)
        return utils.get_object_or_error(FileVersion, getattr(maybe_version, '_id', ''), prefetch_fields=self.serializer_class().model_field_names)
