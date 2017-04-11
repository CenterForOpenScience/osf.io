
from api.addons.views import AddonSettingsMixin
from api.base import permissions as base_permissions
from api.base.exceptions import Conflict
from api.base.filters import ListFilterMixin, ODMFilterMixin
from api.base.parsers import (JSONAPIRelationshipParser,
                              JSONAPIRelationshipParserForRegularJSON)
from api.base.serializers import AddonAccountSerializer
from api.base.utils import (default_node_list_query,
                            default_node_permission_query, get_object_or_error)
from api.base.views import JSONAPIBaseView
from api.institutions.serializers import InstitutionSerializer
from api.nodes.filters import NodePreprintsFilterMixin, NodesListFilterMixin
from api.nodes.serializers import NodeSerializer
from api.preprints.serializers import PreprintSerializer
from api.registrations.serializers import RegistrationSerializer
from api.users.permissions import (CurrentUser, ReadOnlyOrCurrentUser,
                                   ReadOnlyOrCurrentUserRelationship)
from api.users.serializers import (UserAddonSettingsSerializer,
                                   UserDetailSerializer,
                                   UserInstitutionsRelationshipSerializer,
                                   UserSerializer)
from django.contrib.auth.models import AnonymousUser
from framework.auth.oauth_scopes import CoreScopes
from modularodm import Q
from rest_framework import permissions as drf_permissions
from rest_framework import generics
from rest_framework.exceptions import NotAuthenticated, NotFound
from website.models import ExternalAccount, Node, User


class UserMixin(object):
    """Mixin with convenience methods for retrieving the current user based on the
    current URL. By default, fetches the user based on the user_id kwarg.
    """

    serializer_class = UserSerializer
    user_lookup_url_kwarg = 'user_id'

    def get_user(self, check_permissions=True):
        key = self.kwargs[self.user_lookup_url_kwarg]

        if self.kwargs.get('is_embedded') is True:
            if key in self.request.parents[User]:
                return self.request.parents[key]

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
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Users_users_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.RequiresScopedRequestOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = UserSerializer

    ordering = ('-date_registered')
    view_category = 'users'
    view_name = 'user-list'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_registered', 'eq', True) &
            Q('date_disabled', 'eq', None)
        )
        if self.request.version >= '2.3':
            return base_query & Q('merged_by', 'eq', None)
        return base_query

    # overrides ListCreateAPIView
    def get_queryset(self):
        # TODO: sort
        query = self.get_query_from_request()
        return User.find(query)


class UserDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, UserMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Users_users_read).
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
        return self.get_addon_settings(check_object_permissions=False)


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
        return self.get_addon_settings(check_object_permissions=False).external_accounts

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
        user_settings = self.get_addon_settings(check_object_permissions=False)
        account_id = self.kwargs['account_id']

        account = ExternalAccount.load(account_id)
        if not (account and user_settings.external_accounts.filter(id=account.id).exists()):
            raise NotFound('Requested addon unavailable')
        return account


class UserNodes(JSONAPIBaseView, generics.ListAPIView, UserMixin, NodePreprintsFilterMixin, NodesListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Users_users_nodes_list).
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
        return Node.find(self.get_query_from_request()).select_related('node_license').include('guids', 'contributor__user__guids', 'root__guids', limit_includes=10)


class UserPreprints(UserNodes):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Users_users_preprints_list).
    """
    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintSerializer
    view_category = 'users'
    view_name = 'user-preprints'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        user = self.get_user()

        query = (
            Q('is_deleted', 'ne', True) &
            Q('contributors', 'eq', user) &
            Q('preprint_file', 'ne', None) &
            Q('is_public', 'eq', True)
        )

        return query

    def get_queryset(self):
        # Overriding the default query parameters if the provider filter is present, because the provider is stored on
        # the PreprintService object, not the node itself
        filter_key = 'filter[provider]'
        provider_filter = None

        if filter_key in self.request.query_params:
            # Have to have this mutable so that the filter can be removed in the ODM query, otherwise it will return an
            # empty set
            self.request.GET._mutable = True
            provider_filter = self.request.query_params[filter_key]
            self.request.query_params.pop(filter_key)

        nodes = Node.find(self.get_query_from_request())
        preprints = []
        # TODO [OSF-7090]: Rearchitect how `.is_preprint` is determined,
        # so that a query that is guaranteed to return only
        # preprints can be constructed.
        for node in nodes:
            for preprint in node.preprints.all():
                if provider_filter is None or preprint.provider._id == provider_filter:
                    preprints.append(preprint)
        return preprints

class UserInstitutions(JSONAPIBaseView, generics.ListAPIView, UserMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Users_users_institutions_list.
    """
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
        return user.affiliated_institutions.all()


class UserRegistrations(UserNodes):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#Users_users_registrations_list).
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
            Q('is_deleted', 'ne', True) &
            Q('type', 'eq', 'osf.registration') &
            Q('contributors', 'eq', user)
        )
        permission_query = Q('is_public', 'eq', True)
        if not current_user.is_anonymous():
            permission_query = (permission_query | Q('contributors', 'eq', current_user))
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
            'data': user.affiliated_institutions.all(),
            'self': user
        }
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        data = self.request.data['data']
        user = self.request.user
        current_institutions = set(user.affiliated_institutions.values_list('_id', flat=True))

        # DELETEs normally dont get type checked
        # not the best way to do it, should be enforced everywhere, maybe write a test for it
        for val in data:
            if val['type'] != self.serializer_class.Meta.type_:
                raise Conflict()
        for val in data:
            if val['id'] in current_institutions:
                user.remove_institution(val['id'])
        user.save()
