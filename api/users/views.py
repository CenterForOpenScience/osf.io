import pytz

from django.apps import apps
from django.db.models import F
from guardian.shortcuts import get_objects_for_user
from rest_framework.throttling import UserRateThrottle

from api.addons.views import AddonSettingsMixin
from api.base import permissions as base_permissions
from api.base.waffle_decorators import require_flag
from api.base.exceptions import Conflict, UserGone
from api.base.filters import ListFilterMixin, PreprintFilterMixin
from api.base.parsers import (
    JSONAPIRelationshipParser,
    JSONAPIRelationshipParserForRegularJSON,
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.serializers import get_meta_type, AddonAccountSerializer
from api.base.utils import (
    default_node_list_permission_queryset,
    get_object_or_error,
    get_user_auth,
    hashids,
    is_truthy,
)
from api.base.views import JSONAPIBaseView, WaterButlerMixin
from api.base.throttling import SendEmailThrottle, SendEmailDeactivationThrottle, NonCookieAuthThrottle, BurstRateThrottle
from api.institutions.serializers import InstitutionSerializer
from api.nodes.filters import NodesFilterMixin, UserNodesFilterMixin
from api.nodes.serializers import DraftRegistrationLegacySerializer
from api.nodes.utils import NodeOptimizationMixin
from api.osf_groups.serializers import GroupSerializer
from api.preprints.serializers import PreprintSerializer
from api.registrations.serializers import RegistrationSerializer

from api.users.permissions import (
    CurrentUser, ReadOnlyOrCurrentUser,
    ReadOnlyOrCurrentUserRelationship,
    ClaimUserPermission,
)
from api.users.serializers import (
    UserAddonSettingsSerializer,
    UserDetailSerializer,
    UserIdentitiesSerializer,
    UserInstitutionsRelationshipSerializer,
    UserSerializer,
    UserEmail,
    UserEmailsSerializer,
    UserNodeSerializer,
    UserSettingsSerializer,
    UserSettingsUpdateSerializer,
    UserQuickFilesSerializer,
    UserAccountExportSerializer,
    ReadEmailUserDetailSerializer,
    UserChangePasswordSerializer,
)
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.utils import timezone
from framework.auth.core import get_user
from framework.auth.views import send_confirm_email
from framework.auth.oauth_scopes import CoreScopes, normalize_scopes
from framework.auth.exceptions import ChangePasswordError
from framework.utils import throttle_period_expired
from framework.sessions.utils import remove_sessions_for_user
from framework.exceptions import PermissionsError, HTTPError
from osf.features import OSF_GROUPS
from rest_framework import permissions as drf_permissions
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import NotAuthenticated, NotFound, ValidationError, Throttled
from osf.models import (
    Contributor,
    ExternalAccount,
    Guid,
    QuickFilesNode,
    AbstractNode,
    Preprint,
    Node,
    Registration,
    OSFGroup,
    OSFUser,
    Email,
)
from website import mails, settings
from website.project.views.contributor import send_claim_email, send_claim_registered_email

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
            contrib_id, contrib = list(self.request.parents[Contributor].items())[0]
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
                    display_name='user',
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
                display_name='user',
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
        return OSFUser.objects.filter(is_registered=True, date_disabled__isnull=True, merged_by__isnull=True)

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
    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

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
        sorted(qs, key=lambda addon: addon.id, reverse=True)
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


class UserNodes(JSONAPIBaseView, generics.ListAPIView, UserMixin, UserNodesFilterMixin, NodeOptimizationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/users_nodes_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    model_class = AbstractNode

    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_BASE_WRITE]

    serializer_class = UserNodeSerializer
    view_category = 'users'
    view_name = 'user-nodes'

    ordering = ('-last_logged',)

    # overrides NodesFilterMixin

    def get_default_queryset(self):
        user = self.get_user()
        # Nodes the requested user has read_permissions on
        default_queryset = user.nodes_contributor_or_group_member_to
        if user != self.request.user:
            # Further restrict UserNodes to nodes the *requesting* user can view
            return Node.objects.get_nodes_for_user(self.request.user, base_queryset=default_queryset, include_public=True)
        return self.optimize_node_queryset(default_queryset)

    # overrides ListAPIView
    def get_queryset(self):
        return (
            self.get_queryset_from_request()
            .select_related('node_license')
            .include('contributor__user__guids', 'root__guids', limit_includes=10)
        )


class UserGroups(JSONAPIBaseView, generics.ListAPIView, UserMixin, ListFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.NULL]

    model_class = apps.get_model('osf.OSFGroup')
    serializer_class = GroupSerializer
    view_category = 'users'
    view_name = 'user-groups'
    ordering = ('-modified', )

    @require_flag(OSF_GROUPS)
    def get_default_queryset(self):
        requested_user = self.get_user()
        current_user = self.request.user
        if current_user.is_anonymous:
            return OSFGroup.objects.none()
        return requested_user.osf_groups.filter(id__in=current_user.osf_groups.values_list('id', flat=True))

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


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
        default_qs = Preprint.objects.filter(_contributors__guids___id=target_user._id).exclude(machine_state='initial')
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
        # OSF group members not copied to registration.  Only registration contributors need to be checked here.
        return qs.filter(contributor__user__id=user.id)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request().select_related('node_license').include('contributor__user__guids', 'root__guids', limit_includes=10)

class UserDraftRegistrations(JSONAPIBaseView, generics.ListAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_DRAFT_REGISTRATIONS_WRITE]

    serializer_class = DraftRegistrationLegacySerializer
    view_category = 'users'
    view_name = 'user-draft-registrations'

    ordering = ('-modified',)

    def get_queryset(self):
        user = self.get_user()
        # Returns DraftRegistrations for which the user is a contributor, and the user can view
        drafts = user.draft_registrations_active
        return get_objects_for_user(user, 'read_draft_registration', drafts, with_superuser=False)


class UserInstitutionsRelationship(JSONAPIBaseView, generics.RetrieveDestroyAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReadOnlyOrCurrentUserRelationship,
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
            'self': user,
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
            if val['type'] != get_meta_type(self.serializer_class, self.request):
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
        for key, value in user.external_identity.items():
            identities.append({'_id': key, 'external_id': list(value.keys())[0], 'status': list(value.values())[0]})

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

        return {'_id': identity_id, 'external_id': list(identity.keys())[0], 'status': list(identity.values())[0]}

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
    throttle_classes = [UserRateThrottle, NonCookieAuthThrottle, BurstRateThrottle, SendEmailThrottle]

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


class UserChangePassword(JSONAPIBaseView, generics.CreateAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.USER_SETTINGS_WRITE]

    view_category = 'users'
    view_name = 'user_password'

    serializer_class = UserChangePasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.get_user()
        existing_password = request.data['existing_password']
        new_password = request.data['new_password']

        # It has been more than 1 hour since last invalid attempt to change password. Reset the counter for invalid attempts.
        if throttle_period_expired(user.change_password_last_attempt, settings.TIME_RESET_CHANGE_PASSWORD_ATTEMPTS):
            user.reset_old_password_invalid_attempts()

        # There have been more than 3 failed attempts and throttle hasn't expired.
        if user.old_password_invalid_attempts >= settings.INCORRECT_PASSWORD_ATTEMPTS_ALLOWED and not throttle_period_expired(
            user.change_password_last_attempt, settings.CHANGE_PASSWORD_THROTTLE,
        ):
            time_since_throttle = (timezone.now() - user.change_password_last_attempt.replace(tzinfo=pytz.utc)).total_seconds()
            wait_time = settings.CHANGE_PASSWORD_THROTTLE - time_since_throttle
            raise Throttled(wait=wait_time)

        try:
            # double new password for confirmation because validation is done on the front-end.
            user.change_password(existing_password, new_password, new_password)
        except ChangePasswordError as error:
            # A response object must be returned instead of raising an exception to avoid rolling back the transaction
            # and losing the incrementation of failed password attempts
            user.save()
            return JsonResponse(
                {'errors': [{'detail': message} for message in error.messages]},
                status=400,
                content_type='application/vnd.api+json; application/json',
            )

        user.save()
        remove_sessions_for_user(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserSettings(JSONAPIBaseView, generics.RetrieveUpdateAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.USER_SETTINGS_READ]
    required_write_scopes = [CoreScopes.USER_SETTINGS_WRITE]
    throttle_classes = (SendEmailDeactivationThrottle, )

    view_category = 'users'
    view_name = 'user_settings'

    serializer_class = UserSettingsSerializer

    # overrides RetrieveUpdateAPIView
    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserSettingsUpdateSerializer
        return UserSettingsSerializer

    # overrides RetrieveUpdateAPIView
    def get_object(self):
        return self.get_user()


class ClaimUser(JSONAPIBaseView, generics.CreateAPIView, UserMixin):
    permission_classes = (
        base_permissions.TokenHasScope,
        ClaimUserPermission,
    )

    required_read_scopes = [CoreScopes.NULL]  # Tokens should not be able to access this
    required_write_scopes = [CoreScopes.NULL]  # Tokens should not be able to access this

    view_category = 'users'
    view_name = 'claim-user'

    def _send_claim_email(self, *args, **kwargs):
        """ This avoids needing to reimplement all of the logic in the sender methods.
        When v1 is more fully deprecated, those send hooks should be reworked to not
        rely upon a flask context and placed in utils (or elsewhere).
        :param bool registered: Indicates which sender to call (passed in as keyword)
        :param *args: Positional arguments passed to senders
        :param **kwargs: Keyword arguments passed to senders
        :return: None
        """
        from website.app import app
        from website.routes import make_url_map
        try:
            make_url_map(app)
        except AssertionError:
            # Already mapped
            pass
        ctx = app.test_request_context()
        ctx.push()
        if kwargs.pop('registered', False):
            send_claim_registered_email(*args, **kwargs)
        else:
            send_claim_email(*args, **kwargs)
        ctx.pop()

    def post(self, request, *args, **kwargs):
        claimer = request.user
        email = (request.data.get('email', None) or '').lower().strip()
        record_id = (request.data.get('id', None) or '').lower().strip()
        if not record_id:
            raise ValidationError('Must specify record "id".')
        claimed_user = self.get_user(check_permissions=True)  # Ensures claimability
        if claimed_user.is_disabled:
            raise ValidationError('Cannot claim disabled account.')
        try:
            record_referent = Guid.objects.get(_id=record_id).referent
        except Guid.DoesNotExist:
            raise NotFound('Unable to find specified record.')

        try:
            unclaimed_record = claimed_user.unclaimed_records[record_referent._id]
        except KeyError:
            if isinstance(record_referent, Preprint) and record_referent.node and record_referent.node._id in claimed_user.unclaimed_records:
                record_referent = record_referent.node
                unclaimed_record = claimed_user.unclaimed_records[record_referent._id]
            else:
                raise NotFound('Unable to find specified record.')

        if claimer.is_anonymous and email:
            claimer = get_user(email=email)
            try:
                if claimer and claimer.is_registered:
                    self._send_claim_email(claimer, claimed_user, record_referent, registered=True)
                else:
                    self._send_claim_email(email, claimed_user, record_referent, notify=True, registered=False)
            except HTTPError as e:
                raise ValidationError(e.data['message_long'])
        elif isinstance(claimer, OSFUser):
            if unclaimed_record.get('referrer_id', '') == claimer._id:
                raise ValidationError('Referrer cannot claim user.')
            try:
                self._send_claim_email(claimer, claimed_user, record_referent, registered=True)
            except HTTPError as e:
                raise ValidationError(e.data['message_long'])

        else:
            raise ValidationError('Must either be logged in or specify claim email.')
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserEmailsList(JSONAPIBaseView, generics.ListAPIView, generics.CreateAPIView, UserMixin, ListFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.USER_SETTINGS_READ]
    required_write_scopes = [CoreScopes.USER_SETTINGS_WRITE]

    throttle_classes = [UserRateThrottle, NonCookieAuthThrottle, BurstRateThrottle, SendEmailThrottle]

    view_category = 'users'
    view_name = 'user-emails'

    serializer_class = UserEmailsSerializer

    def get_default_queryset(self):
        user = self.get_user()
        serialized_emails = []
        for email in user.emails.all():
            primary = email.address == user.username
            hashed_id = hashids.encode(email.id)
            serialized_email = UserEmail(email_id=hashed_id, address=email.address, confirmed=True, verified=True, primary=primary)
            serialized_emails.append(serialized_email)
        email_verifications = user.email_verifications or {}
        for token, detail in email_verifications.items():
            is_merge = Email.objects.filter(address=detail['email']).exists()
            serialized_unconfirmed_email = UserEmail(
                email_id=token,
                address=detail['email'],
                confirmed=detail['confirmed'],
                verified=False,
                primary=False,
                is_merge=is_merge,
            )
            serialized_emails.append(serialized_unconfirmed_email)

        return serialized_emails

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class UserEmailsDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.USER_SETTINGS_READ]
    required_write_scopes = [CoreScopes.USER_SETTINGS_WRITE]

    view_category = 'users'
    view_name = 'user-email-detail'

    serializer_class = UserEmailsSerializer

    # Overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        email_id = self.kwargs['email_id']
        user = self.get_user()
        email = None

        # check to see if it's a confirmed email with hashed id
        decoded_id = hashids.decode(email_id)
        if decoded_id:
            try:
                email = user.emails.get(id=decoded_id[0])
            except Email.DoesNotExist:
                email = None
            else:
                primary = email.address == user.username
                address = email.address
                confirmed = True
                verified = True
                is_merge = False

        # check to see if it's an unconfirmed email with a token
        elif user.unconfirmed_emails:
            try:
                email = user.email_verifications[email_id]
                address = email['email']
                confirmed = email['confirmed']
                verified = False
                primary = False
                is_merge = Email.objects.filter(address=address).exists()
            except KeyError:
                email = None

        if not email:
            raise NotFound

        # check for resend confirmation email query parameter in a GET request
        if self.request.method == 'GET' and is_truthy(self.request.query_params.get('resend_confirmation')):
            if not confirmed and settings.CONFIRM_REGISTRATIONS_BY_EMAIL:
                if throttle_period_expired(user.email_last_sent, settings.SEND_EMAIL_THROTTLE):
                    send_confirm_email(user, email=address, renew=True)
                    user.email_last_sent = timezone.now()
                    user.save()

        return UserEmail(email_id=email_id, address=address, confirmed=confirmed, verified=verified, primary=primary, is_merge=is_merge)

    def get(self, request, *args, **kwargs):
        response = super(UserEmailsDetail, self).get(request, *args, **kwargs)
        if is_truthy(self.request.query_params.get('resend_confirmation')):
            user = self.get_user()
            email_id = kwargs.get('email_id')
            if user.unconfirmed_emails and user.email_verifications.get(email_id):
                response.status = response.status_code = status.HTTP_202_ACCEPTED
        return response

    # Overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        user = self.get_user()
        email = instance.address
        if instance.confirmed and instance.verified:
            try:
                user.remove_email(email)
            except PermissionsError as e:
                raise ValidationError(e.args[0])
        else:
            user.remove_unconfirmed_email(email)
            user.save()
