from rest_framework import generics
from rest_framework import permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes

from website.files.models import FileNode
from website.files.models import FileVersion

from api.base.permissions import PermissionWithGetter
from api.base.utils import get_object_or_error
from api.base import permissions as base_permissions
from api.nodes.permissions import ContributorOrPublic
from api.nodes.permissions import ReadOnlyIfRegistration
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
        obj = get_object_or_error(FileNode, self.kwargs[self.file_lookup_url_kwarg])

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        return obj.wrapped()


class FileDetail(generics.RetrieveUpdateAPIView, FileMixin):
    """Details about files and folders. *Writeable*.

    So if you GET a self link for a file, it will return the file itself for downloading. If you GET a related link for
    a file, you'll get the metadata about the file. GETting a related link for a folder will get you the listing of
    what's in that folder. GETting a folder's self link won't work, because there's nothing to get.

    Which brings us to the other useful thing about the links here: there's a field called `self-methods`. This field
    will tell you what the valid methods are for the self links given the kind of thing they are (file vs folder) and
    given your permissions on the object.

    NOTE: Most of the API will be stable as far as how the links work because the things they are accessing are fairly
    stable and predictable, so if you felt the need, you could construct them in the normal REST way and they should
    be fine.
    The 'self' links from the NodeFilesList may have to change from time to time, so you are highly encouraged to use
    the links as we provide them before you use them, and not to reverse engineer the structure of the links as they
    are at any given time.

    ##Attributes

    `type` is "files"

    Both files and folders are accessed through this endpoint and may be distinguished by the `kind` attribute. `size`
    will be `null` for folders.

        name           type               description
        ---------------------------------------------------------------------------------
        name          string             name of the file or folder
        kind          string             "file" or "folder"
        path          url path           path to this entity, used in "move" actions
        size          integer            size of file in bytes, null for folders
        provider      string             storage provider for this file. "osfstorage" if stored on the OSF.  Other
                                         examples include "s3" for Amazon S3, "googledrive" for Google Drive, "box"
                                         for Box.com.
        last_touched  iso8601 timestamp  last time the metadata for the file was retrieved. only applies to non-OSF
                                         storage providers.

    ##Relationships

    ###Checkout

    **TODO**

    ###Files (*folders*)

    The `files` endpoint lists all of the subfiles and folders of the current folder. Will be `null` for files.

    ###Versions (*files*)

    The `versions` endpoint provides version history for files.  Will be `null` for folders.

    ##Links

        info:        the canonical api endpoint for the latest version of the file
        new_folder:  url to target when creating new subfolders
        move:        url to target for move, copy, and rename actions
        upload:      url to target for uploading new files and updating existing files
        download:    url to request a download of the latest version of the file
        delete:      url to target for deleting files and folders

    ##Actions

    The `links` property of the response provides endpoints for common file operations. The currently-supported actions
    are:

    ###Get Info (*files, folders*)

        Method:   GET
        URL:      links.info
        Params:   <none>
        Success:  200 OK + file representation

    The details of a particular file can be retrieved by performing a GET request against the `info` link.

    ###Download (*files*)

        Method:   GET
        URL:      links.download
        Params:   <none>
        Success:  200 OK + file body

    To download a file, issue a GET request against the `download` link.  The response will have the Content-Disposition
    header set, which will will trigger a download in a browser.

    ###Create Subfolder (*folders*)

        Method:       PUT
        URL:          links.new_folder
        Query Params: ?name=<new folder name>
        Body:         <empty>
        Success:      201 Created + new folder representation

    You can create a subfolder of an existing folder by issuing a PUT request against the `new_folder` link.  The name
    of the new subfolder should be provided in the `name` query parameter.  The response will contain the following:

        name          type               description
        ---------------------------------------------------------------------------------
        name          string             name of the new folder
        path          url path           path of the folder in **OSF or Waterbutler**?
        materialized  string             the full path of the folder relative to the storage root
        kind          string             "folder"
        etag          string             **TODO**
        extra         object             **TODO**

    ###Upload New File (*folders*)

        Method:       PUT
        URL:          links.upload
        Query Params: ?kind=file&name=<new file name>
        Body (Raw):   <file data (not form-encoded)>
        Success:      201 Created + new file representation

    To upload a file to a folder, issue a PUT request to the folder's `upload` link with the raw file data in the
    request body, and the `kind` and `name` query parameters set to `'file'` and the desired name of the file.  The
    response will describe the new file.

        name          type               description
        ---------------------------------------------------------------------------------
        name          string             name of the new folder
        path          url path           path of the folder in **OSF or Waterbutler**?
        materialized  string             the full path of the folder relative to the storage root
        kind          string             "file"
        etag          string             **TODO**
        modified      timestamp          **TODO**
        contentType   string             null if provider="osfstorage", else MIME-type
        provider      string             id of provider e.g. "osfstorage", "s3", "googledrive"
        size          integer            size of file in bytes
        extra         object
          version     integer            version number of file. will be 1 on initial upload
          downloads   integer            count of the number times the file has been downloaded
          hashes      object
            md5       string             md5 hash of file
            sha256    string             SHA-256 hash of file

    ###Update Existing File (*file*)

        Method:       PUT
        URL:          links.upload
        Query Params: kind=file&name=<new file name>
        Body (Raw):   <file data (not form-encoded)>
        Success:      200 OK + updated file representation

    To update an existing file, issue a PUT request to the file's `upload` link with the raw file data in the request
    body, and the `kind` and `name` query parameters set to `"file"` and the desired name of the file.  The update
    action will create a new version of the file.  The response format is the same as the **Upload New File** action.

    ###Rename (*files, folders*)

        Method:        POST
        URL:           links.move
        Query Params:  <none>
        Body (JSON):   {
                        "action": "rename",
                        "rename": <new file name>
                       }
        Success:       200 OK + new entity representation

    To rename a file or folder, issue a POST request to the `move` link with the `action` body parameter set to
    `"rename"` and the `rename` body parameter set to the desired name.  The response format is the same as the **Upload
    New File** action, except if the renamed entity is a folder, `kind` will be `"folder"`.

    ###Move & Copy (*files, folders*)

        Method:        POST
        URL:           links.move
        Query Params:  <none>
        Body (JSON):   {
                        // mandatory
                        "action":   "move|copy",
                        "path":     <path attribute of target folder>,
                        // optional
                        "rename":   <new name>,
                        "conflict": "replace|keep" // defaults to 'replace'
                       }
        Succes:        200 OK + new entity representation

    Move and copy actions both use the same request structure, a POST to the `move` url, but with different values for
    the `action` body parameters.  The `path` parameter is also required and should be the `path` attribute of the
    folder being written to.  The `rename` and `conflict` parameters are optional.  If you wish to change the name of
    the file or folder at its destination, set the `rename` parameter to the new name.  The `conflict` param governs how
    name clashes are resolved.  Possible values are `replace` and `keep`.  `replace` is the default and will overwrite
    the file that already exists in the target folder.  `keep` will attempt to keep both by adding a suffix to the new
    file's name until it no longer conflicts.  The suffix will be ' (**x**)' where **x** is a increasing integer starting
    from 1.  This behavior is intended to simulate that of the OS X Finder.

    ###Delete (*file, folders*)

        Method:        DELETE
        URL:           links.delete
        Query Params:  <none>
        Success:       204 No Content

    To delete a file or folder send a DELETE request to the `delete` link.  Nothing will be returned in the response
    body.

    ##Query Params

    For this endpoint, *none*.  Actions may permit or require certain query parameters.  See the individual action
    documentation.

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CheckedOutOrAdmin,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, 'node'),
        PermissionWithGetter(ReadOnlyIfRegistration, 'node'),
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileDetailSerializer

    def get_node(self):
        return self.get_file().node

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_file()


class FileVersionsList(generics.ListAPIView, FileMixin):
    """List of versions for the requested file. *Read-only*.

    Paginated list of file versions, ordered by increasing version number (id).

    ##FileVersion Attributes

    **TODO: import from FileVersionDetail**

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    File versions may be filtered by their `id`, `size`, or `content_type`.

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, 'node'),
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileVersionSerializer

    def get_queryset(self):
        return self.get_file().versions


def node_from_version(request, view, obj):
    return view.get_file(check_permissions=False).node


class FileVersionDetail(generics.RetrieveAPIView, FileMixin):
    """Details about a specific file version. *Read-only*.

    ##Attributes

    `type` is "file_version"

        name          type     description
        ---------------------------------------------------------------------------------
        size          integer  size of file in bytes
        content_type  string   MIME content-type for the file. May be null if file is stored locally.

    ##Relationships

    *None*.

    ##Links

        self:  the canonical api endpoint for this version of the file
        html:  the OSF webpage for this file version

    ##Actions

    *None*.

    ##Query Params

    *None*.

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

    # overrides RetrieveAPIView
    def get_object(self):
        file = self.get_file()
        maybe_version = file.get_version(self.kwargs[self.version_lookup_url_kwarg])

        # May raise a permission denied
        # Kinda hacky but versions have no reference to node or file
        self.check_object_permissions(self.request, file)
        return get_object_or_error(FileVersion, getattr(maybe_version, '_id', ''))
