
from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotAuthenticated, NotFound
from django.contrib.auth.models import AnonymousUser

from modularodm import Q

from framework.auth.oauth_scopes import CoreScopes

from website.models import User, Node, ExternalAccount

from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.base.exceptions import Conflict
from api.base.serializers import AddonAccountSerializer
from api.base.views import JSONAPIBaseView
from api.base.filters import ODMFilterMixin, ListFilterMixin
from api.base.parsers import JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON
from api.nodes.serializers import NodeSerializer
from api.institutions.serializers import InstitutionSerializer
from api.registrations.serializers import RegistrationSerializer
from api.base.utils import default_node_list_query, default_node_permission_query
from api.addons.views import AddonSettingsMixin

from .serializers import UserSerializer, UserAddonSettingsSerializer, UserDetailSerializer, UserInstitutionsRelationshipSerializer, PublicFilesSerializer
from .permissions import ReadOnlyOrCurrentUser, ReadOnlyOrCurrentUserRelationship, CurrentUser


class UserMixin(object):
    """Mixin with convenience methods for retrieving the current user based on the
    current URL. By default, fetches the user based on the user_id kwarg.
    """

    serializer_class = UserSerializer
    user_lookup_url_kwarg = 'user_id'

    def get_user(self, check_permissions=True):
        key = self.kwargs[self.user_lookup_url_kwarg]
        current_user = self.request.user

        if key == 'me':
            if isinstance(current_user, AnonymousUser):
                raise NotAuthenticated
            else:
                return self.request.user

        obj = get_object_or_error(User, key, 'user')
        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        return obj


class UserList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """List of users registered on the OSF. *Read-only*.

    Paginated list of users ordered by the date they registered.  Each resource contains the full representation of the
    user, meaning additional requests to an individual user's detail view are not necessary.

    Note that if an anonymous view_only key is being used, user information will not be serialized, and the id will be
    an empty string. Relationships to a user object will not show in this case, either.

    The subroute [`/me/`](me/) is a special endpoint that always points to the currently logged-in user.

    ##User Attributes

    <!--- Copied Attributes From UserDetail -->

    OSF User entities have the "users" `type`.

        name               type               description
        ========================================================================================
        full_name          string             full name of the user; used for display
        given_name         string             given name of the user; for bibliographic citations
        middle_names       string             middle name of user; for bibliographic citations
        family_name        string             family name of user; for bibliographic citations
        suffix             string             suffix of user's name for bibliographic citations
        date_registered    iso8601 timestamp  timestamp when the user's account was created

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Users may be filtered by their `id`, `full_name`, `given_name`, `middle_names`, or `family_name`.

    + `profile_image_size=<Int>` -- Modifies `/links/profile_image_url` of the user entities so that it points to
    the user's profile image scaled to the given size in pixels.  If left blank, the size depends on the image provider.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE]

    serializer_class = UserSerializer

    ordering = ('-date_registered')
    view_category = 'users'
    view_name = 'user-list'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('is_registered', 'eq', True) &
            Q('is_merged', 'ne', True) &
            Q('date_disabled', 'eq', None)
        )

    # overrides ListAPIView
    def get_queryset(self):
        # TODO: sort
        query = self.get_query_from_request()
        return User.find(query)


class UserDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, UserMixin):
    """Details about a specific user. *Writeable*.

    The User Detail endpoint retrieves information about the user whose id is the final part of the path.  If `me`
    is given as the id, the record of the currently logged-in user will be returned.  The returned information includes
    the user's bibliographic information and the date the user registered.

    Note that if an anonymous view_only key is being used, user information will not be serialized, and the id will be
    an empty string. Relationships to a user object will not show in this case, either.

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

    ##Relationships

    ###Nodes

    A list of all nodes the user has contributed to.  If the user id in the path is the same as the logged-in user, all
    nodes will be visible.  Otherwise, you will only be able to see the other user's publicly-visible nodes.

    ##Links

        self:               the canonical api endpoint of this user
        html:               this user's page on the OSF website
        profile_image_url:  a url to the user's profile image

    ##Actions

    ###Update

        Method:        PUT / PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "users",   # required
                           "id":   {user_id}, # required
                           "attributes": {
                             "full_name":    {full_name},    # mandatory
                             "given_name":   {given_name},   # optional
                             "middle_names": {middle_names}, # optional
                             "family_name":  {family_name},  # optional
                             "suffix":       {suffix}        # optional
                           }
                         }
                       }
        Success:       200 OK + node representation

    To update your user profile, issue a PUT request to either the canonical URL of your user resource (as given in
    `/links/self`) or to `/users/me/`.  Only the `full_name` attribute is required.  Unlike at signup, the given, middle,
    and family names will not be inferred from the `full_name`.  Currently, only `full_name`, `given_name`,
    `middle_names`, `family_name`, and `suffix` are updateable.

    A PATCH request issued to this endpoint will behave the same as a PUT request, but does not require `full_name` to
    be set.

    **NB:** If you PUT/PATCH to the `/users/me/` endpoint, you must still provide your full user id in the `id` field of
    the request.  We do not support using the `me` alias in request bodies at this time.

    ##Query Params

    + `profile_image_size=<Int>` -- Modifies `/links/profile_image_url` so that it points the image scaled to the given
    size in pixels.  If left blank, the size depends on the image provider.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyOrCurrentUser,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE]
    view_category = 'users'
    view_name = 'user-detail'

    serializer_class = UserDetailSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_user()

    # overrides RetrieveUpdateAPIView
    def get_serializer_context(self):
        # Serializer needs the request in order to make an update to privacy
        context = JSONAPIBaseView.get_serializer_context(self)
        context['request'] = self.request
        return context


class UserAddonList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, UserMixin):
    """List of addons authorized by this user *Read-only*

    Paginated list of user addons ordered by their `id` or `addon_short_name`.

    ###Permissions

    <Addon>UserSettings are visible only to the user that "owns" them.

    ## <Addon\>UserSettings Attributes

    OSF <Addon\>UserSettings entities have the "user_addons" `type`, and their `id` indicates the addon
    service provider (eg. `box`, `googledrive`, etc).

        name                type        description
        =====================================================================================
        user_has_auth       boolean     does this user have access to use an ExternalAccount?

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

        self:  the canonical api endpoint of this user_addon
        accounts: dict keyed on an external_account_id
            nodes_connected:    list of canonical api endpoints of connected nodes
            account:            canonical api endpoint for this account

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.USER_ADDON_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = UserAddonSettingsSerializer
    view_category = 'users'
    view_name = 'user-addons'

    def get_queryset(self):
        qs = [addon for addon in self.get_user().get_addons() if 'accounts' in addon.config.configs]
        qs.sort()
        return qs


class UserAddonDetail(JSONAPIBaseView, generics.RetrieveAPIView, UserMixin, AddonSettingsMixin):
    """Detail of an individual addon authorized by this user *Read-only*

    ##Permissions

    <Addon>UserSettings are visible only to the user that "owns" them.

    ## <Addon\>UserSettings Attributes

    OSF <Addon\>UserSettings entities have the "user_addons" `type`, and their `id` indicates the addon
    service provider (eg. `box`, `googledrive`, etc).

        name                type        description
        =====================================================================================
        user_has_auth       boolean     does this user have access to use an ExternalAccount?

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

        self:  the canonical api endpoint of this user_addon
        accounts: dict keyed on an external_account_id
            nodes_connected:    list of canonical api endpoints of connected nodes
            account:            canonical api endpoint for this account

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.USER_ADDON_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = UserAddonSettingsSerializer
    view_category = 'users'
    view_name = 'user-addon-detail'

    def get_object(self):
        return self.get_addon_settings()


class UserAddonAccountList(JSONAPIBaseView, generics.ListAPIView, UserMixin, AddonSettingsMixin):
    """List of an external_accounts authorized by this user *Read-only*

    ##Permissions

    ExternalAccounts are visible only to the user that has ownership of them.

    ## ExternalAccount Attributes

    OSF ExternalAccount entities have the "external_accounts" `type`, with `id` indicating the
    `external_account_id` according to the OSF

        name            type        description
        =====================================================================================================
        display_name    string      Display name on the third-party service
        profile_url     string      Link to users profile on third-party service *presence varies by service*
        provider        string      short_name of third-party service provider

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

        self:  the canonical api endpoint of this external_account

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.USER_ADDON_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = AddonAccountSerializer
    view_category = 'users'
    view_name = 'user-external_accounts'

    def get_queryset(self):
        return self.get_addon_settings().external_accounts

class UserAddonAccountDetail(JSONAPIBaseView, generics.RetrieveAPIView, UserMixin, AddonSettingsMixin):
    """Detail of an individual external_account authorized by this user *Read-only*

    ##Permissions

    ExternalAccounts are visible only to the user that has ownership of them.

    ## ExternalAccount Attributes

    OSF ExternalAccount entities have the "external_accounts" `type`, with `id` indicating the
    `external_account_id` according to the OSF

        name            type        description
        =====================================================================================================
        display_name    string      Display name on the third-party service
        profile_url     string      Link to users profile on third-party service *presence varies by service*
        provider        string      short_name of third-party service provider

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

        self:  the canonical api endpoint of this external_account

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.USER_ADDON_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = AddonAccountSerializer
    view_category = 'users'
    view_name = 'user-external_account-detail'

    def get_object(self):
        user_settings = self.get_addon_settings()
        account_id = self.kwargs['account_id']

        account = ExternalAccount.load(account_id)
        if not (account and account in user_settings.external_accounts):
            raise NotFound('Requested addon unavailable')
        return account


class UserNodes(JSONAPIBaseView, generics.ListAPIView, UserMixin, ODMFilterMixin):
    """List of nodes that the user contributes to. *Read-only*.

    Paginated list of nodes that the user contributes to ordered by `date_modified`.  User registrations are not available
    at this endpoint. Each resource contains the full representation of the node, meaning additional requests to an individual
    node's detail view are not necessary. If the user id in the path is the same as the logged-in user, all nodes will be
    visible.  Otherwise, you will only be able to see the other user's publicly-visible nodes.  The special user id `me`
    can be used to represent the currently logged-in user.

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
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        registration                    boolean            is this a registration? (always false - may be deprecated in future versions)
        fork                            boolean            is this node a fork of another node?
        public                          boolean            has this node been made publicly-visible?
        collection                      boolean            is this a collection? (always false - may be deprecated in future versions)

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    <!--- Copied Query Params from NodeList -->

    Nodes may be filtered by their `id`, `title`, `category`, `description`, `public`, `tags`, `date_created`, `date_modified`,
    `root`, `parent`, and `contributors`.  Most are string fields and will be filtered using simple substring matching.  `public`
    is a boolean, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.  Note that quoting `true`
    or `false` in the query will cause the match to fail regardless.  `tags` is an array of simple strings.


    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_BASE_WRITE]

    serializer_class = NodeSerializer
    view_category = 'users'
    view_name = 'user-nodes'

    ordering = ('-date_modified',)

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        user = self.get_user()
        query = Q('contributors', 'eq', user) & default_node_list_query()
        if user != self.request.user:
            query &= default_node_permission_query(self.request.user)
        return query

    # overrides ListAPIView
    def get_queryset(self):
        return Node.find(self.get_query_from_request())


class UserInstitutions(JSONAPIBaseView, generics.ListAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = InstitutionSerializer
    view_category = 'users'
    view_name = 'user-institutions'

    def get_default_odm_query(self):
        return None

    def get_queryset(self):
        user = self.get_user()
        return user.affiliated_institutions


class UserRegistrations(UserNodes):
    """List of registrations that the user contributes to. *Read-only*.

    Paginated list of registrations that the user contributes to.  Each resource contains the full representation of the
    registration, meaning additional requests to an individual registration's detail view are not necessary. If the user
    id in the path is the same as the logged-in user, all nodes will be visible.  Otherwise, you will only be able to
    see the other user's publicly-visible nodes.  The special user id `me` can be used to represent the currently
    logged-in user.

    A withdrawn registration will display a limited subset of information, namely, title, description,
    date_created, registration, withdrawn, date_registered, withdrawal_justification, and registration supplement. All
    other fields will be displayed as null. Additionally, the only relationships permitted to be accessed for a withdrawn
    registration are the contributors - other relationships will return a 403.

    ##Registration Attributes

    <!--- Copied Attributes from RegistrationList -->

    Registrations have the "registrations" `type`.

        name                            type               description
        =======================================================================================================
        title                           string             title of the registered project or component
        description                     string             description of the registered node
        category                        string             bode category, must be one of the allowed values
        date_created                    iso8601 timestamp  timestamp that the node was created
        date_modified                   iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the registered node
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        fork                            boolean            is this project a fork?
        registration                    boolean            has this project been registered? (always true - may be deprecated in future versions)
        collection                      boolean            is this registered node a collection? (always false - may be deprecated in future versions)
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


    ##Relationships

    ###Registered from

    The registration is branched from this node.

    ###Registered by

    The registration was initiated by this user.

    ###Other Relationships

    See documentation on registered_from detail view.  A registration has many of the same properties as a node.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    <!--- Copied Query Params from NodeList -->

     Registrations may be filtered by their `id`, `title`, `category`, `description`, `public`, `tags`, `date_created`, `date_modified`,
    `root`, `parent`, and `contributors`.  Most are string fields and will be filtered using simple substring matching.  `public`
    is a boolean, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.  Note that quoting `true`
    or `false` in the query will cause the match to fail regardless.  `tags` is an array of simple strings.

    #This Request/Response

    """
    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = RegistrationSerializer
    view_category = 'users'
    view_name = 'user-registrations'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        user = self.get_user()
        current_user = self.request.user

        query = (
            Q('is_collection', 'ne', True) &
            Q('is_deleted', 'ne', True) &
            Q('is_registration', 'eq', True) &
            Q('contributors', 'eq', user._id)
        )
        permission_query = Q('is_public', 'eq', True)
        if not current_user.is_anonymous():
            permission_query = (permission_query | Q('contributors', 'eq', current_user._id))
        query = query & permission_query
        return query


class UserInstitutionsRelationship(JSONAPIBaseView, generics.RetrieveDestroyAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReadOnlyOrCurrentUserRelationship
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE]

    serializer_class = UserInstitutionsRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    view_category = 'users'
    view_name = 'user-institutions-relationship'

    def get_object(self):
        user = self.get_user(check_permissions=False)
        obj = {
            'data': user.affiliated_institutions,
            'self': user
        }
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        data = self.request.data['data']
        user = self.request.user
        current_institutions = {inst._id for inst in user.affiliated_institutions}

        # DELETEs normally dont get type checked
        # not the best way to do it, should be enforced everywhere, maybe write a test for it
        for val in data:
            if val['type'] != self.serializer_class.Meta.type_:
                raise Conflict()
        for val in data:
            if val['id'] in current_institutions:
                user.remove_institution(val['id'])
        user.save()

class UserPublicFiles(JSONAPIBaseView, generics.ListAPIView, UserMixin, ODMFilterMixin):
    view_name = 'user-public-files'
    view_category = 'users'
    serializer_class = PublicFilesSerializer

    def get_queryset(self):

        return Node.find(Q('contributors', 'eq', self.get_user()._id) & Q('is_public_files_collection', 'eq', True))
