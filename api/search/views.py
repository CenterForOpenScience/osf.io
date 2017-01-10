# -*- coding: utf-8 -*-

from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import ValidationError

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.pagination import SearchPagination
from api.base.settings import REST_FRAMEWORK, MAX_PAGE_SIZE
from api.files.serializers import FileSerializer
from api.nodes.serializers import NodeSerializer
from api.registrations.serializers import RegistrationSerializer
from api.search.serializers import SearchSerializer
from api.users.serializers import UserSerializer

from framework.auth.oauth_scopes import CoreScopes

from osf.models import FileNode, AbstractNode as Node, OSFUser as User
from website.search import search
from website.search.exceptions import MalformedQueryError
from website.search.util import build_query


class BaseSearchView(JSONAPIBaseView, generics.ListAPIView):

    required_read_scopes = [CoreScopes.SEARCH]
    required_write_scopes = [CoreScopes.NULL]

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    pagination_class = SearchPagination

    def __init__(self):
        super(BaseSearchView, self).__init__()
        self.doc_type = getattr(self, 'doc_type', None)

    def get_queryset(self):
        query = self.request.query_params.get('q', '*')
        page = int(self.request.query_params.get('page', '1'))
        page_size = min(int(self.request.query_params.get('page[size]', REST_FRAMEWORK['PAGE_SIZE'])), MAX_PAGE_SIZE)
        start = (page - 1) * page_size
        try:
            results = search.search(build_query(query, start=start, size=page_size), doc_type=self.doc_type, raw=True)
        except MalformedQueryError as e:
            raise ValidationError(e.message)
        return results


class Search(BaseSearchView):
    """
    *Read-Only*

    Objects (including projects, components, registrations, users, and files) that have been found by the given
    Elasticsearch query. Each object is serialized with the appropriate serializer for its type (files are serialized as
    files, users are serialized as users, etc.) and returned collectively.

    ## Search Fields

        <type>  # either projects, components, registrations, users, or files
            related
                href    # the canonical api endpoint to search within a certain object type, e.g `/v2/search/users/`
                meta
                    total   # the number of results found that are of the enclosing object type

    ## Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ## Query Params

    + `q=<Str>` -- Query to search projects, components, registrations, users, and files for.

    + `page=<Int>` -- page number of results to view, default 1

    # This Request/Response

    """

    serializer_class = SearchSerializer

    view_category = 'search'
    view_name = 'search-search'


class SearchComponents(BaseSearchView):
    """
    *Read-Only*

    Components that have been found by the given Elasticsearch query.

    <!--- Copied piel from NodeDetail -->

    On the front end, nodes are considered 'projects' or 'components'. The difference between a project and a component
    is that a project is the top-level node, and components are children of the project. There is also a [category
    field](/v2/#osf-node-categories) that includes 'project' as an option. The categorization essentially determines
    which icon is displayed by the node in the front-end UI and helps with search organization. Top-level nodes may have
    a category other than project, and children nodes may have a category of project.

    ##Node Attributes

    <!--- Copied Attributes from NodeDetail -->

    OSF Node entities have the "nodes" `type`.

        name                            type               description
        =================================================================================
        title                           string             title of project or component
        description                     string             description of the node
        category                        string             node category, must be one of the allowed values
        date_created                    iso8601 timestamp  timestamp that the node was created
        date_modified                   iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        registration                    boolean            is this a registration? (always false - may be deprecated in future versions)
        fork                            boolean            is this node a fork of another node?
        public                          boolean            has this node been made publicly-visible?
        preprint                        boolean            is this a preprint?
        collection                      boolean            is this a collection? (always false - may be deprecated in future versions)
        node_license                    object             details of the license applied to the node
            year                        string             date range of the license
            copyright_holders           array of strings   holders of the applied license

    ##Relationships

    ###Children

    List of nodes that are children of this node.  New child nodes may be added through this endpoint.

    ###Comments

    List of comments on this node.  New comments can be left on the node through this endpoint.

    ###Contributors

    List of users who are contributors to this node. Contributors may have "read", "write", or "admin" permissions.
    A node must always have at least one "admin" contributor.  Contributors may be added via this endpoint.

    ###Draft Registrations

    List of draft registrations of the current node.

    ###Files

    List of top-level folders (actually cloud-storage providers) associated with this node. This is the starting point
    for accessing the actual files stored within this node.

    ###Forked From

    If this node was forked from another node, the canonical endpoint of the node that was forked from will be
    available in the `/forked_from/links/related/href` key.  Otherwise, it will be null.

    ###Logs

    List of read-only log actions pertaining to the node.

    ###Node Links

    List of links (pointers) to other nodes on the OSF.  Node links can be added through this endpoint.

    ###Parent

    If this node is a child node of another node, the parent's canonical endpoint will be available in the
    `/parent/links/related/href` key.  Otherwise, it will be null.

    ###Registrations

    List of registrations of the current node.

    ###Root

    Returns the top-level node associated with the current node.  If the current node is the top-level node, the root is
    the current node.

    ##Links

        self:  the canonical api endpoint of this node
        html:  this node's page on the OSF website

        See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Query Params

    + `q=<Str>` -- Query to search components for, searches across a component's title, description, tags, and contributor names.

    + `page=<Int>` -- page number of results to view, default 1

    #This Request/Response

    """

    model_class = Node
    serializer_class = NodeSerializer

    doc_type = 'component'
    view_category = 'search'
    view_name = 'search-component'


class SearchFiles(BaseSearchView):
    """
    *Read-Only*

    Files that have been found by the given Elasticsearch query.

    <!-- Copied attributes from FileDetail -->

    ####File Entity

        name          type       description
        =========================================================================
        guid          string            OSF GUID for this file (if one has been assigned)
        name          string            name of the file
        path          string            unique identifier for this file entity for this
                                        project and storage provider. may not end with '/'
        materialized  string            the full path of the file relative to the storage
                                        root.  may not end with '/'
        kind          string            "file"
        etag          string            etag - http caching identifier w/o wrapping quotes
        modified      timestamp         last modified timestamp - format depends on provider
        contentType   string            MIME-type when available
        provider      string            id of provider e.g. "osfstorage", "s3", "googledrive".
                                        equivalent to addon_short_name on the OSF
        size          integer           size of file in bytes
        tags          array of strings  list of tags that describes the file (osfstorage only)
        extra         object            may contain additional data beyond what's described here,
                                        depending on the provider
          version     integer           version number of file. will be 1 on initial upload
          downloads   integer           count of the number times the file has been downloaded
          hashes      object
            md5       string            md5 hash of file
            sha256    string            SHA-256 hash of file

    ##Attributes

    For an OSF File entity, the `type` is "files" regardless of whether the entity is actually a file or folder, because
    it belongs to the `files` collection of the API.  They can be distinguished by the `kind` attribute.  Files and
    folders use the same representation, but some attributes may be null for one kind but not the other. `size` will be
    null for folders.  A list of storage provider keys can be found [here](/v2/#storage-providers).

        name                        type               description
        ================================================================================================================
        name                        string             name of the file or folder; used for display
        kind                        string             "file" or "folder"
        path                        string             same as for corresponding WaterButler entity
        materialized_path           string             the unix-style path to the file relative to the provider root
        size                        integer            size of file in bytes, null for folders
        provider                    string             storage provider for this file. "osfstorage" if stored on the
                                                         OSF.  other examples include "s3" for Amazon S3, "googledrive"
                                                        for Google Drive, "box" for Box.com.
        current_user_can_comment    boolean            Whether the current user is allowed to post comments

        last_touched                iso8601 timestamp  last time the metadata for the file was retrieved. only
                                                        applies to non-OSF storage providers.
        date_modified               iso8601 timestamp  timestamp of when this file was last updated*
        date_created                iso8601 timestamp  timestamp of when this file was created*
        extra                       object             may contain additional data beyond what's described here,
                                                        depending on the provider
        hashes                      object
        md5                         string             md5 hash of file, null for folders
        sha256                      string             SHA-256 hash of file, null for folders

    * A note on timestamps: for files stored in osfstorage, `date_created` refers to the time the file was
    first uploaded to osfstorage, and `date_modified` is the time the file was last updated while in osfstorage.
    Other providers may or may not provide this information, but if they do it will correspond to the provider's
    semantics for created/modified times.  These timestamps may also be stale; metadata retrieved via the File Detail
    endpoint is cached.  The `last_touched` field describes the last time the metadata was retrieved from the external
    provider.  To force a metadata update, access the parent folder via its Node Files List endpoint.

    <!-- Copied relationships from FileDetail -->

    ##Relationships

    ###Node

    The `node` endpoint describes the project or registration that this file belongs to.

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

    ## Query Params

    + `q=<Str>` -- Query to search files for, searches across a file's name.

    + `page=<Int>` -- page number of results to view, default 1

    #This Request/Response

    """

    model_class = FileNode
    serializer_class = FileSerializer

    doc_type = 'file'
    view_category = 'search'
    view_name = 'search-file'


class SearchProjects(BaseSearchView):
    """
    *Read-Only*

    Projects that have been found by the given Elasticsearch query.

    <!--- Copied spiel from NodeDetail -->

    On the front end, nodes are considered 'projects' or 'components'. The difference between a project and a component
    is that a project is the top-level node, and components are children of the project. There is also a [category
    field](/v2/#osf-node-categories) that includes 'project' as an option. The categorization essentially determines
    which icon is displayed by the node in the front-end UI and helps with search organization. Top-level nodes may have
    a category other than project, and children nodes may have a category of project.

    ##Node Attributes

    <!--- Copied Attributes from NodeDetail -->

    OSF Node entities have the "nodes" `type`.

        name                            type               description
        =================================================================================
        title                           string             title of project or component
        description                     string             description of the node
        category                        string             node category, must be one of the allowed values
        date_created                    iso8601 timestamp  timestamp that the node was created
        date_modified                   iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        registration                    boolean            is this a registration? (always false - may be deprecated in future versions)
        fork                            boolean            is this node a fork of another node?
        public                          boolean            has this node been made publicly-visible?
        preprint                        boolean            is this a preprint?
        collection                      boolean            is this a collection? (always false - may be deprecated in future versions)
        node_license                    object             details of the license applied to the node
            year                        string             date range of the license
            copyright_holders           array of strings   holders of the applied license

    ##Relationships

    ###Children

    List of nodes that are children of this node.  New child nodes may be added through this endpoint.

    ###Comments

    List of comments on this node.  New comments can be left on the node through this endpoint.

    ###Contributors

    List of users who are contributors to this node. Contributors may have "read", "write", or "admin" permissions.
    A node must always have at least one "admin" contributor.  Contributors may be added via this endpoint.

    ###Draft Registrations

    List of draft registrations of the current node.

    ###Files

    List of top-level folders (actually cloud-storage providers) associated with this node. This is the starting point
    for accessing the actual files stored within this node.

    ###Forked From

    If this node was forked from another node, the canonical endpoint of the node that was forked from will be
    available in the `/forked_from/links/related/href` key.  Otherwise, it will be null.

    ###Logs

    List of read-only log actions pertaining to the node.

    ###Node Links

    List of links (pointers) to other nodes on the OSF.  Node links can be added through this endpoint.

    ###Parent

    If this node is a child node of another node, the parent's canonical endpoint will be available in the
    `/parent/links/related/href` key.  Otherwise, it will be null.

    ###Registrations

    List of registrations of the current node.

    ###Root

    Returns the top-level node associated with the current node.  If the current node is the top-level node, the root is
    the current node.

    ##Links

        self:  the canonical api endpoint of this node
        html:  this node's page on the OSF website

        See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Query Params

    + `q=<Str>` -- Query to search projects for, searches across a project's title, description, tags, and contributor names.

    + `page=<Int>` -- page number of results to view, default 1


    #This Request/Response

    """

    model_class = Node
    serializer_class = NodeSerializer

    doc_type = 'project'
    view_category = 'search'
    view_name = 'search-project'


class SearchRegistrations(BaseSearchView):
    """
    *Read-Only*

    Registrations that have been found by the given Elasticsearch query.

    <!--- Copied spiel from RegistrationDetail -->

    Node Registrations.

    Registrations are read-only snapshots of a project. This view is a list of all current registrations for which a user
    has access.  A withdrawn registration will display a limited subset of information, namely, title, description,
    date_created, registration, withdrawn, date_registered, withdrawal_justification, and registration supplement. All
    other fields will be displayed as null. Additionally, the only relationships permitted to be accessed for a withdrawn
    registration are the contributors - other relationships will return a 403.

    Each resource contains the full representation of the registration, meaning additional requests to an individual
    registrations's detail view are not necessary.  Unregistered nodes cannot be accessed through this endpoint.

    <!--- Copied attributes from RegistrationDetail -->
    ##Registration Attributes

    Registrations have the "registrations" `type`.

        name                            type               description
        =======================================================================================================
        title                           string             title of the registered project or component
        description                     string             description of the registered node
        category                        string             bode category, must be one of the allowed values
        date_created                    iso8601 timestamp  timestamp that the node was created
        date_modified                   iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the registered node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        fork                            boolean            is this project a fork?
        registration                    boolean            has this project been registered? (always true - may be deprecated in future versions)
        collection                      boolean            is this registered node a collection? (always false - may be deprecated in future versions)
        node_license                    object             details of the license applied to the node
        year                            string             date range of the license
        copyright_holders               array of strings   holders of the applied license
        public                          boolean            has this registration been made publicly-visible?
        withdrawn                       boolean            has this registration been withdrawn?
        date_registered                 iso8601 timestamp  timestamp that the registration was created
        embargo_end_date                iso8601 timestamp  when the embargo on this registration will be lifted (if applicable)
        withdrawal_justification        string             reasons for withdrawing the registration
        pending_withdrawal              boolean            is this registration pending withdrawal?
        pending_withdrawal_approval     boolean            is this registration pending approval?
        pending_embargo_approval        boolean            is the associated Embargo awaiting approval by project admins?
        registered_meta                 dictionary         registration supplementary information
        registration_supplement         string             registration template


    <!--- Copied relationships from RegistrationDetail -->
    ##Relationships

    ###Registered from

    The registration is branched from this node.

    ###Registered by

    The registration was initiated by this user.

    ###Other Relationships

    See documentation on registered_from detail view.  A registration has many of the same properties as a node.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ## Query Params

    + `q=<Str>` -- Query to search registrations for, searches across a registration's title, description, tags, and contributor names.

    + `page=<Int>` -- page number of results to view, default 1

    #This Request/Response

    """

    model_class = Node
    serializer_class = RegistrationSerializer

    doc_type = 'registration'
    view_category = 'search'
    view_name = 'search-registration'


class SearchUsers(BaseSearchView):
    """
    *Read-Only*

    Users that have been found by the given Elasticsearch query.

    <!-- Copied spiel from UserDetail -->

    The User Detail endpoint retrieves information about the user whose id is the final part of the path.  If `me`
    is given as the id, the record of the currently logged-in user will be returned.  The returned information includes
    the user's bibliographic information and the date the user registered.

    Note that if an anonymous view_only key is being used, user information will not be serialized, and the id will be
    an empty string. Relationships to a user object will not show in this case, either.

    <!-- Copied attributes from UserDetail -->

    ##Attributes

    OSF User entities have the "users" `type`.

        name               type               description
        ========================================================================================
        full_name          string             full name of the user; used for display
        given_name         string             given name of the user; for bibliographic citations
        middle_names       string             middle name of user; for bibliographic citations
        family_name        string             family name of user; for bibliographic citations
        suffix             string             suffix of user's name for bibliographic citations
        date_registered    iso8601 timestamp  timestamp when the user's account was created

    <!-- Copied relationships from UserDetail -->

    ##Relationships

    ###Nodes

    A list of all nodes the user has contributed to.  If the user id in the path is the same as the logged-in user, all
    nodes will be visible.  Otherwise, you will only be able to see the other user's publicly-visible nodes.

    ##Links

        self:               the canonical api endpoint of this user
        html:               this user's page on the OSF website
        profile_image_url:  a url to the user's profile image

    ## Query Params

    + `q=<Str>` -- Query to search users for, searches across a users's given name, middle names, family name,
    first listed job, and first listed school.

    + `page=<Int>` -- page number of results to view, default 1

    # This Request/Response

    """

    model_class = User
    serializer_class = UserSerializer

    doc_type = 'user'
    view_category = 'search'
    view_name = 'search-user'
