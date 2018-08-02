from django.apps import apps
from django.db.models import F

from api.addons.views import AddonSettingsMixin
from api.base import permissions as base_permissions
from api.base.exceptions import Conflict, UserGone
from api.base.filters import ListFilterMixin, PreprintFilterMixin
from api.base.parsers import (JSONAPIRelationshipParser,
                              JSONAPIRelationshipParserForRegularJSON)
from api.base.serializers import AddonAccountSerializer
from api.base.utils import (default_node_list_queryset,
                            default_node_list_permission_queryset,
                            get_object_or_error,
                            get_user_auth)
from api.base.views import JSONAPIBaseView, WaterButlerMixin
from api.base.throttling import SendEmailThrottle
from api.institutions.serializers import InstitutionSerializer
from api.nodes.filters import NodesFilterMixin
from api.nodes.serializers import NodeSerializer
from api.preprints.serializers import PreprintSerializer
from api.registrations.serializers import RegistrationSerializer
from api.users.permissions import (CurrentUser, ReadOnlyOrCurrentUser,
                                   ReadOnlyOrCurrentUserRelationship)
from api.users.serializers import (UserAddonSettingsSerializer,
                                   UserDetailSerializer,
                                   UserIdentitiesSerializer,
                                   UserInstitutionsRelationshipSerializer,
                                   UserSerializer,
                                   UserQuickFilesSerializer,
                                   UserAccountExportSerializer,
                                   UserAccountDeactivateSerializer,
                                   ReadEmailUserDetailSerializer,)
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from framework.auth.oauth_scopes import CoreScopes, normalize_scopes
from rest_framework import permissions as drf_permissions
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import NotAuthenticated, NotFound
from osf.models import (Contributor,
                        ExternalAccount,
                        QuickFilesNode,
                        AbstractNode,
                        PreprintService,
                        Node,
                        Registration,
                        OSFUser)
from website import mails, settings


class UserMixin(object):
    """Mixin with convenience methods for retrieving the current user based on the
    current URL. By default, fetches the user based on the user_id kwarg.
    """

    serializer_class = UserSerializer
    user_lookup_url_kwarg = 'user_id'

    def get_user(self, check_permissions=True):
        key = self.kwargs[self.user_lookup_url_kwarg]
        # If Contributor is in self.request.parents,
        # then this view is getting called due to an embedded request (contributor embedding user)
        # We prefer to access the user from the contributor object and take advantage
        # of the query cache
        if hasattr(self.request, 'parents') and len(self.request.parents.get(Contributor, {})) == 1:
            # We expect one parent contributor view, so index into the first item
            contrib_id, contrib = self.request.parents[Contributor].items()[0]
            user = contrib.user
            if user.is_disabled:
                raise UserGone(user=user)
            # Make sure that the contributor ID is correct
            if user._id == key:
                if check_permissions:
                    self.check_object_permissions(self.request, user)
                return get_object_or_error(
                    OSFUser.objects.filter(id=user.id).annotate(default_region=F('addons_osfstorage_user_settings__default_region___id')).exclude(default_region=None),
                    request=self.request,
                    display_name='user'
                )

        if self.kwargs.get('is_embedded') is True:
            if key in self.request.parents[OSFUser]:
                return self.request.parents[OSFUser].get(key)

        current_user = self.request.user

        if isinstance(current_user, AnonymousUser):
            if key == 'me':
                raise NotAuthenticated

        elif key == 'me' or key == current_user._id:
            return get_object_or_error(
                OSFUser.objects.filter(id=current_user.id).annotate(default_region=F('addons_osfstorage_user_settings__default_region___id')).exclude(default_region=None),
                request=self.request,
                display_name='user'
            )

        obj = get_object_or_error(OSFUser, key, self.request, 'user')

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        return obj


class UserList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/users_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.RequiresScopedRequestOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = apps.get_model('osf.OSFUser')

    serializer_class = UserSerializer

    ordering = ('-date_registered')
    view_category = 'users'
    view_name = 'user-list'

    def get_default_queryset(self):
        if self.request.version >= '2.3':
            return OSFUser.objects.filter(is_registered=True, date_disabled__isnull=True, merged_by__isnull=True)
        return OSFUser.objects.filter(is_registered=True, date_disabled__isnull=True)

    # overrides ListCreateAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class UserDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, UserMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/users_read).
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

    def get_serializer_class(self):
        if self.request.auth:
            scopes = self.request.auth.attributes['accessTokenScope']
            if (CoreScopes.USER_EMAIL_READ in normalize_scopes(scopes) and self.request.user == self.get_user()):
                return ReadEmailUserDetailSerializer
        return UserDetailSerializer

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
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/users_addons_list).
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

    ordering = ('-id',)

    def get_queryset(self):
        qs = [addon for addon in self.get_user().get_addons() if 'accounts' in addon.config.configs]
        qs.sort()
        return qs


class UserAddonDetail(JSONAPIBaseView, generics.RetrieveAPIView, UserMixin, AddonSettingsMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/users_addons_read).
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
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/Users_addon_accounts_list).
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

    ordering = ('-date_last_refreshed',)

    def get_queryset(self):
        return self.get_addon_settings(check_object_permissions=False).external_accounts

class UserAddonAccountDetail(JSONAPIBaseView, generics.RetrieveAPIView, UserMixin, AddonSettingsMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/Users_addon_accounts_read).
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


class UserNodes(JSONAPIBaseView, generics.ListAPIView, UserMixin, NodesFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/users_nodes_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    model_class = AbstractNode

    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_BASE_WRITE]

    serializer_class = NodeSerializer
    view_category = 'users'
    view_name = 'user-nodes'

    ordering = ('-modified',)

    # overrides NodesFilterMixin
    def get_default_queryset(self):
        user = self.get_user()
        if user != self.request.user:
            return default_node_list_permission_queryset(user=self.request.user, model_cls=Node).filter(contributor__user__id=user.id)
        return default_node_list_queryset(model_cls=Node).filter(contributor__user__id=user.id)

    # overrides ListAPIView
    def get_queryset(self):
        return (
            self.get_queryset_from_request()
            .select_related('node_license')
            .include('contributor__user__guids', 'root__guids', limit_includes=10)
        )


class UserQuickFiles(JSONAPIBaseView, generics.ListAPIView, WaterButlerMixin, UserMixin, ListFilterMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    ordering = ('-last_touched')

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE]

    serializer_class = UserQuickFilesSerializer
    view_category = 'users'
    view_name = 'user-quickfiles'

    def get_node(self, check_object_permissions):
        return QuickFilesNode.objects.get_for_user(self.get_user(check_permissions=False))

    def get_default_queryset(self):
        self.kwargs[self.path_lookup_url_kwarg] = '/'
        self.kwargs[self.provider_lookup_url_kwarg] = 'osfstorage'
        files_list = self.fetch_from_waterbutler()

        return files_list.children.prefetch_related('versions', 'tags').include('guids')

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class UserPreprints(JSONAPIBaseView, generics.ListAPIView, UserMixin, PreprintFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/users_preprints_list).
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    ordering = ('-created')
    model_class = AbstractNode

    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintSerializer
    view_category = 'users'
    view_name = 'user-preprints'

    def get_default_queryset(self):
        # the user who is requesting
        auth = get_user_auth(self.request)
        auth_user = getattr(auth, 'user', None)

        # the user data being requested
        target_user = self.get_user(check_permissions=False)

        # Permissions on the list objects are handled by the query
        default_qs = PreprintService.objects.filter(node___contributors__guids___id=target_user._id)
        return self.preprints_queryset(default_qs, auth_user, allow_contribs=False)

    def get_queryset(self):
        return self.get_queryset_from_request()


class UserInstitutions(JSONAPIBaseView, generics.ListAPIView, UserMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/users_institutions_list).
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

    ordering = ('-pk', )

    def get_default_odm_query(self):
        return None

    def get_queryset(self):
        user = self.get_user()
        return user.affiliated_institutions.all()


class UserRegistrations(JSONAPIBaseView, generics.ListAPIView, UserMixin, NodesFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/users_registrations_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    model_class = Registration

    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = RegistrationSerializer
    view_category = 'users'
    view_name = 'user-registrations'

    ordering = ('-modified',)

    # overrides NodesFilterMixin
    def get_default_queryset(self):
        user = self.get_user()
        current_user = self.request.user
        qs = default_node_list_permission_queryset(user=current_user, model_cls=Registration)
        return qs.filter(contributor__user__id=user.id)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request().select_related('node_license').include('contributor__user__guids', 'root__guids', limit_includes=10)


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


class UserIdentitiesList(JSONAPIBaseView, generics.ListAPIView, UserMixin):
    """
    The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/external_identities_list).
    """
    permission_classes = (
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
        CurrentUser,
    )

    serializer_class = UserIdentitiesSerializer

    required_read_scopes = [CoreScopes.USER_SETTINGS_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'users'
    view_name = 'user-identities-list'

    # overrides ListAPIView
    def get_queryset(self):
        user = self.get_user()
        identities = []
        for key, value in user.external_identity.iteritems():
            identities.append({'_id': key, 'external_id': value.keys()[0], 'status': value.values()[0]})

        return identities


class UserIdentitiesDetail(JSONAPIBaseView, generics.RetrieveDestroyAPIView, UserMixin):
    """
    The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/external_identities_detail).
    """
    permission_classes = (
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.USER_SETTINGS_READ]
    required_write_scopes = [CoreScopes.USER_SETTINGS_WRITE]

    serializer_class = UserIdentitiesSerializer

    view_category = 'users'
    view_name = 'user-identities-detail'

    def get_object(self):
        user = self.get_user()
        identity_id = self.kwargs['identity_id']
        try:
            identity = user.external_identity[identity_id]
        except KeyError:
            raise NotFound('Requested external identity could not be found.')

        return {'_id': identity_id, 'external_id': identity.keys()[0], 'status': identity.values()[0]}

    def perform_destroy(self, instance):
        user = self.get_user()
        identity_id = self.kwargs['identity_id']
        try:
            user.external_identity.pop(identity_id)
        except KeyError:
            raise NotFound('Requested external identity could not be found.')

        user.save()


class UserAccountExport(JSONAPIBaseView, generics.CreateAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.USER_SETTINGS_WRITE]

    view_category = 'users'
    view_name = 'user-account-export'

    serializer_class = UserAccountExportSerializer
    throttle_classes = (SendEmailThrottle, )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.get_user()
        mails.send_mail(
            to_addr=settings.OSF_SUPPORT_EMAIL,
            mail=mails.REQUEST_EXPORT,
            user=user,
            can_change_preferences=False,
        )
        user.email_last_sent = timezone.now()
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserAccountDeactivate(JSONAPIBaseView, generics.CreateAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.USER_SETTINGS_WRITE]

    view_category = 'users'
    view_name = 'user-account-deactivate'

    serializer_class = UserAccountDeactivateSerializer
    throttle_classes = (SendEmailThrottle, )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.get_user()
        mails.send_mail(
            to_addr=settings.OSF_SUPPORT_EMAIL,
            mail=mails.REQUEST_DEACTIVATION,
            user=user,
            can_change_preferences=False,
        )
        user.email_last_sent = timezone.now()
        user.requested_deactivation = True
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
