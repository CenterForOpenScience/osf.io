from rest_framework import generics
from rest_framework import permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes

from website.files.models import FileNode
from website.files.models import FileVersion

from api.base.permissions import PermissionWithGetter
from api.base.utils import get_object_or_error
from api.base.views import JSONAPIBaseView
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


class FileDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, FileMixin):
    """Details about files and folders. *Writeable*.

    Welcome to the Files API.  Brace yourself, things are about to get *weird*.

    The Files API is the one place in the OSF API where we break hard from the JSON-API spec.  This is because most of
    the behind-the-scenes moving, uploading, deleting, etc. of files and folders is actually handled for us by a
    nifty piece of software called [WaterButler](https://github.com/CenterForOpenScience/waterbutler).  WaterButler lets
    us interact with files stored on different cloud storage platforms through a consistent API.  However, it uses
    different conventions for requests, responses, and URL-building, so pay close attention to the documentation for
    [actions](#actions).  The exception is the "Get Info" action, which is OSF-centric.

    Only files and folders which have previously been retrieved through the Node Files List endpoint (accessible through
    the `files` relationship of their parent nodes) can be accessed through this endpoint.  Viewing a folder through the
    Node Files List vivifies their children's metadata in the OSF and allows the children to be assigned ids.  This
    metadata is cached and can be refreshed by GETting the file via the Node Files List endpoint.

    Both files and folders are available through the Files API and are distinguished by the `kind` attribute ("file" for
    files, "folder" for folders).  Not all actions and relationships are relevant to both files and folders, so the
    applicable types are listed by each heading.

    ###Waterbutler Entities

    When an action is performed against a WaterButler endpoint, it will generally respond with a file entity, a folder
    entity, or no content.

    ####File Entity

        name          type       description
        -------------------------------------------------------------------------
        name          string     name of the file
        path          string     unique identifier for this file entity for this
                                 project and storage provider. may not end with '/'
        materialized  string     the full path of the file relative to the storage
                                 root.  may not end with '/'
        kind          string     "file"
        etag          string     etag - http caching identifier w/o wrapping quotes
        modified      timestamp  last modified timestamp - format depends on provider
        contentType   string     MIME-type when available
        provider      string     id of provider e.g. "osfstorage", "s3", "googledrive".
                                 equivalent to addon_short_name on the OSF
        size          integer    size of file in bytes
        extra         object     may contain additional data beyond what's described here,
                                 depending on the provider
          version     integer    version number of file. will be 1 on initial upload
          downloads   integer    count of the number times the file has been downloaded
          hashes      object
            md5       string     md5 hash of file
            sha256    string     SHA-256 hash of file

    ####Folder Entity

        name          type    description
        ----------------------------------------------------------------------
        name          string  name of the folder
        path          string  unique identifier for this folder entity for this
                              project and storage provider. must end with '/'
        materialized  string  the full path of the folder relative to the storage
                              root.  must end with '/'
        kind          string  "folder"
        etag          string  etag - http caching identifier w/o wrapping quotes
        extra         object  varies depending on provider


    ##Attributes

    For an OSF File entity, the `type` is "files" regardless of whether the entity is actually a file or folder, because
    it belongs to the `files` collection of the API.  They can be distinguished by the `kind` attribute.  Files and
    folders use the same representation, but some attributes may be null for one kind but not the other. `size` will be
    null for folders.  A list of storage provider keys can be found [here](/v2/#storage-providers).

        name          type               description
        ---------------------------------------------------------------------------------------------------
        name              string             name of the file or folder; used for display
        kind              string             "file" or "folder"
        path              string             same as for corresponding WaterButler entity
        materialized_path string             the unix-style path to the file relative to the provider root
        size              integer            size of file in bytes, null for folders
        provider          string             storage provider for this file. "osfstorage" if stored on the
                                             OSF.  other examples include "s3" for Amazon S3, "googledrive"
                                             for Google Drive, "box" for Box.com.
        last_touched      iso8601 timestamp  last time the metadata for the file was retrieved. only
                                             applies to non-OSF storage providers.
        date_modified     iso8601 timestamp  timestamp of when this file was last updated*
        date_created      iso8601 timestamp  timestamp of when this file was created*
        extra             object             may contain additional data beyond what's described here,
                                             depending on the provider
          hashes          object
            md5           string             md5 hash of file, null for folders
            sha256        string             SHA-256 hash of file, null for folders

    * A note on timestamps: for files stored in osfstorage, `date_created` refers to the time the file was
    first uploaded to osfstorage, and `date_modified` is the time the file was last updated while in osfstorage.
    Other providers may or may not provide this information, but if they do it will correspond to the provider's
    semantics for created/modified times.  These timestamps may also be stale; metadata retrieved via the File Detail
    endpoint is cached.  The `last_touched` field describes the last time the metadata was retrieved from the external
    provider.  To force a metadata update, access the parent folder via its Node Files List endpoint.

    ##Relationships

    ###Files (*folders*)

    The `files` endpoint lists all of the subfiles and folders of the current folder. Will be null for files.

    ###Versions (*files*)

    The `versions` endpoint provides version history for files.  Will be null for folders.

    ##Links

        info:        the canonical api endpoint for the folder's contents or file's most recent version
        new_folder:  url to target when creating new subfolders (null for files)
        move:        url to target for move, copy, and rename actions
        upload:      url to target for uploading new files and updating existing files
        download:    url to request a download of the latest version of the file (null for folders)
        delete:      url to target for deleting files and folders

    ##Actions

    The `links` property of the response provides endpoints for common file operations. The currently-supported actions
    are:

    ###Get Info (*files, folders*)

        Method:   GET
        URL:      /links/info
        Params:   <none>
        Success:  200 OK + file representation

    The contents of a folder or details of a particular file can be retrieved by performing a GET request against the
    `info` link. The response will be a standard OSF response format with the [OSF File attributes](#attributes).

    ###Download (*files*)

        Method:   GET
        URL:      /links/download
        Params:   <none>
        Success:  200 OK + file body

    To download a file, issue a GET request against the `download` link.  The response will have the Content-Disposition
    header set, which will will trigger a download in a browser.

    ###Create Subfolder (*folders*)

        Method:       PUT
        URL:          /links/new_folder
        Query Params: ?kind=folder&name={new_folder_name}
        Body:         <empty>
        Success:      201 Created + new folder representation

    You can create a subfolder of an existing folder by issuing a PUT request against the `new_folder` link.  The
    `?kind=folder` portion of the query parameter is already included in the `new_folder` link.  The name of the new
    subfolder should be provided in the `name` query parameter.  The response will contain a [WaterButler folder
    entity](#folder-entity).  If a folder with that name already exists in the parent directory, the server will return
    a 409 Conflict error response.

    ###Upload New File (*folders*)

        Method:       PUT
        URL:          /links/upload
        Query Params: ?kind=file&name={new_file_name}
        Body (Raw):   <file data (not form-encoded)>
        Success:      201 Created or 200 OK + new file representation

    To upload a file to a folder, issue a PUT request to the folder's `upload` link with the raw file data in the
    request body, and the `kind` and `name` query parameters set to `'file'` and the desired name of the file.  The
    response will contain a [WaterButler file entity](#file-entity) that describes the new file.  If a file with the
    same name already exists in the folder, it will be considered a new version.  In this case, the response will be a
    200 OK.

    ###Update Existing File (*file*)

        Method:       PUT
        URL:          /links/upload
        Query Params: ?kind=file
        Body (Raw):   <file data (not form-encoded)>
        Success:      200 OK + updated file representation

    To update an existing file, issue a PUT request to the file's `upload` link with the raw file data in the request
    body and the `kind` query parameter set to `"file"`.  The update action will create a new version of the file.
    The response will contain a [WaterButler file entity](#file-entity) that describes the updated file.

    ###Rename (*files, folders*)

        Method:        POST
        URL:           /links/move
        Query Params:  <none>
        Body (JSON):   {
                        "action": "rename",
                        "rename": {new_file_name}
                       }
        Success:       200 OK + new entity representation

    To rename a file or folder, issue a POST request to the `move` link with the `action` body parameter set to
    `"rename"` and the `rename` body parameter set to the desired name.  The response will contain either a folder
    entity or file entity with the new name.

    ###Move & Copy (*files, folders*)

        Method:        POST
        URL:           /links/move
        Query Params:  <none>
        Body (JSON):   {
                        // mandatory
                        "action":   "move"|"copy",
                        "path":     {path_attribute_of_target_folder},
                        // optional
                        "rename":   {new_name},
                        "conflict": "replace"|"keep", // defaults to 'replace'
                        "resource": {node_id},        // defaults to current {node_id}
                        "provider": {provider}        // defaults to current {provider}
                       }
        Success:       200 OK or 201 Created + new entity representation

    Move and copy actions both use the same request structure, a POST to the `move` url, but with different values for
    the `action` body parameters.  The `path` parameter is also required and should be the OSF `path` attribute of the
    folder being written to.  The `rename` and `conflict` parameters are optional.  If you wish to change the name of
    the file or folder at its destination, set the `rename` parameter to the new name.  The `conflict` param governs how
    name clashes are resolved.  Possible values are `replace` and `keep`.  `replace` is the default and will overwrite
    the file that already exists in the target folder.  `keep` will attempt to keep both by adding a suffix to the new
    file's name until it no longer conflicts.  The suffix will be ' (**x**)' where **x** is a increasing integer
    starting from 1.  This behavior is intended to mimic that of the OS X Finder.  The response will contain either a
    folder entity or file entity with the new name.

    Files and folders can also be moved between nodes and providers.  The `resource` parameter is the id of the node
    under which the file/folder should be moved.  It *must* agree with the `path` parameter, that is the `path` must
    identify a valid folder under the node identified by `resource`.  Likewise, the `provider` parameter may be used to
    move the file/folder to another storage provider, but both the `resource` and `path` parameters must belong to a
    node and folder already extant on that provider.  Both `resource` and `provider` default to the current node and
    providers.

    If a moved/copied file is overwriting an existing file, a 200 OK response will be returned.  Otherwise, a 201
    Created will be returned.

    ###Delete (*file, folders*)

        Method:        DELETE
        URL:           /links/delete
        Query Params:  <none>
        Success:       204 No Content

    To delete a file or folder send a DELETE request to the `delete` link.  Nothing will be returned in the response
    body.

    ##Query Params

    For this endpoint, *none*.  Actions may permit or require certain query parameters.  See the individual action
    documentation.

    #This Request/Response

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
    view_category = 'files'
    view_name = 'file-detail'

    def get_node(self):
        return self.get_file().node

    # overrides RetrieveAPIView
    def get_object(self):
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
        ---------------------------------------------------------------------------------
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
        return self.get_file().versions


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
        ---------------------------------------------------------------------------------
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
        return get_object_or_error(FileVersion, getattr(maybe_version, '_id', ''))
