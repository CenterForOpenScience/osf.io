import pytz
from urllib.parse import urlencode

from django.apps import apps
from django.db import IntegrityError
from django.db.models import F
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from guardian.shortcuts import get_objects_for_user
from rest_framework.throttling import UserRateThrottle

from api.addons.views import AddonSettingsMixin
from api.base import permissions as base_permissions
from api.users.permissions import UserMessagePermissions
from api.base.exceptions import Conflict, UserGone, Gone
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
from api.base.views import JSONAPIBaseView
from api.base.throttling import (
    SendEmailThrottle,
    SendEmailDeactivationThrottle,
    NonCookieAuthThrottle,
    BurstRateThrottle,
    RootAnonThrottle,
)
from api.institutions.serializers import InstitutionSerializer
from api.nodes.filters import NodesFilterMixin, UserNodesFilterMixin
from api.nodes.serializers import DraftRegistrationLegacySerializer
from api.nodes.utils import NodeOptimizationMixin
from api.preprints.serializers import PreprintSerializer, PreprintDraftSerializer
from api.registrations import annotations as registration_annotations
from api.registrations.serializers import RegistrationSerializer
from api.resources import annotations as resource_annotations

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
    UserResetPasswordSerializer,
    UserSerializer,
    UserEmail,
    UserEmailsSerializer,
    UserNodeSerializer,
    UserSettingsSerializer,
    UserSettingsUpdateSerializer,
    UserAccountExportSerializer,
    ReadEmailUserDetailSerializer,
    UserChangePasswordSerializer,
    UserMessageSerializer,
    ExternalLoginSerialiser,
    ConfirmEmailTokenSerializer,
    SanctionTokenSerializer,
)
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.utils import timezone
from framework import sentry
from framework.auth.core import get_user, generate_verification_key
from framework.auth.views import send_confirm_email_async, ensure_external_identity_uniqueness
from framework.auth.tasks import update_affiliation_for_orcid_sso_users
from framework.auth.oauth_scopes import CoreScopes, normalize_scopes
from framework.auth.exceptions import ChangePasswordError
from framework.celery_tasks.handlers import enqueue_task
from framework.utils import throttle_period_expired
from framework.sessions.utils import remove_sessions_for_user
from framework.exceptions import PermissionsError, HTTPError
from rest_framework import permissions as drf_permissions
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import NotAuthenticated, NotFound, ValidationError, Throttled
from osf.models import (
    Contributor,
    ExternalAccount,
    Guid,
    AbstractNode,
    Preprint,
    Node,
    Registration,
    OSFUser,
    Email,
    Tag,
)
from osf.utils.tokens import TokenHandler
from osf.utils.tokens.handlers import sanction_handler
from website import mails, settings, language
from website.project.views.contributor import send_claim_email, send_claim_registered_email
from website.util.metrics import CampaignClaimedTags, CampaignSourceTags
from framework.auth import exceptions


class UserMixin:
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
    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON)

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
            .prefetch_related('contributor_set__user__guids', 'root__guids')
        )


class UserQuickFiles(JSONAPIBaseView, generics.ListAPIView):
    view_category = 'users'
    view_name = 'user-quickfiles'

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    def get(self, *args, **kwargs):
        raise Gone()


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
        return self.preprints_queryset(default_qs, auth_user, allow_contribs=False, latest_only=True)

    def get_queryset(self):
        return self.get_queryset_from_request()


class UserDraftPreprints(JSONAPIBaseView, generics.ListAPIView, UserMixin, PreprintFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/).
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    ordering = ('-created')

    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintDraftSerializer
    view_category = 'users'
    view_name = 'user-draft-preprints'

    def get_default_queryset(self):
        user = self.get_user()
        return user.preprints.filter(
            machine_state='initial',
            deleted__isnull=True,
        )

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

    ordering = ('-pk',)

    def get_default_odm_query(self):
        return None

    def get_queryset(self):
        user = self.get_user()
        return user.get_affiliated_institutions()


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
        qs = default_node_list_permission_queryset(
            user=current_user,
            model_cls=Registration,
            revision_state=registration_annotations.REVISION_STATE,
            **resource_annotations.make_open_practice_badge_annotations(),
        )
        # OSF group members not copied to registration.  Only registration contributors need to be checked here.
        return qs.filter(contributor__user__id=user.id)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request().select_related(
            'node_license',
        ).prefetch_related(
            'contributor_set__user__guids',
            'root__guids',
        )

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
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON)

    view_category = 'users'
    view_name = 'user-institutions-relationship'

    def get_object(self):
        user = self.get_user(check_permissions=False)
        obj = {
            'data': user.get_affiliated_institutions(),
            'self': user,
        }
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        data = self.request.data['data']
        user = self.request.user
        current_institutions = set(user.get_institution_affiliations().values_list('institution___id', flat=True))

        # DELETEs normally dont get type checked
        # not the best way to do it, should be enforced everywhere, maybe write a test for it
        for val in data:
            if val['type'] != get_meta_type(self.serializer_class, self.request):
                raise Conflict()
        for val in data:
            if val['id'] in current_institutions:
                user.remove_affiliated_institution(val['id'])
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


class ExternalLogin(JSONAPIBaseView, generics.CreateAPIView):
    """
    View to handle email submission for first-time oauth-login user.
    HTTP Method: POST
    """
    permission_classes = (
        drf_permissions.AllowAny,
    )
    serializer_class = ExternalLoginSerialiser
    view_category = 'users'
    view_name = 'external-login'

    throttle_classes = (NonCookieAuthThrottle, BurstRateThrottle, RootAnonThrottle)

    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = request.session
        external_id_provider = session.get('auth_user_external_id_provider', None)
        external_id = session.get('auth_user_external_id', None)
        fullname = session.get('auth_user_fullname', None) or request.data.get('auth_user_fullname', None)

        accepted_terms_of_service = request.data.get('accepted_terms_of_service', False)

        if session.get('auth_user_external_first_login', False) is not True:
            raise HTTPError(status.HTTP_401_UNAUTHORIZED)

        clean_email = request.data.get('email', None)
        user = get_user(email=clean_email)
        external_identity = {
            external_id_provider: {
                external_id: None,
            },
        }
        try:
            ensure_external_identity_uniqueness(external_id_provider, external_id, user)
        except ValidationError as e:
            raise HTTPError(status.HTTP_403_FORBIDDEN, e.message)
        if user:
            # 1. update user oauth, with pending status
            external_identity[external_id_provider][external_id] = 'LINK'
            if external_id_provider in user.external_identity:
                user.external_identity[external_id_provider].update(external_identity[external_id_provider])
            else:
                user.external_identity.update(external_identity)
            if not user.accepted_terms_of_service and accepted_terms_of_service:
                user.accepted_terms_of_service = timezone.now()
            # 2. add unconfirmed email and send confirmation email
            user.add_unconfirmed_email(clean_email, external_identity=external_identity)
            user.save()
            send_confirm_email_async(
                user,
                clean_email,
                external_id_provider=external_id_provider,
                external_id=external_id,
            )

        else:
            # 1. create unconfirmed user with pending status
            external_identity[external_id_provider][external_id] = 'CREATE'
            accepted_terms_of_service = timezone.now() if accepted_terms_of_service else None
            user = OSFUser.create_unconfirmed(
                username=clean_email,
                password=None,
                fullname=fullname,
                external_identity=external_identity,
                campaign=None,
                accepted_terms_of_service=accepted_terms_of_service,
            )
            # TODO: [#OSF-6934] update social fields, verified social fields cannot be modified
            user.save()
            # 3. send confirmation email
            send_confirm_email_async(
                user,
                user.username,
                external_id_provider=external_id_provider,
                external_id=external_id,
            )

        # Don't go anywhere
        return JsonResponse(
            {
                'external_id_provider': external_id_provider,
                'auth_user_fullname': fullname,
            },
            status=status.HTTP_200_OK,
            content_type='application/vnd.api+json; application/json',
        )

class ResetPassword(JSONAPIBaseView, generics.ListCreateAPIView):
    """
    View for handling reset password requests.

    GET:
    - Takes an email as a query parameter.
    - If the email is associated with an OSF account, sends an email with instructions to reset the password.
    - If the email is not provided or invalid, returns a validation error.
    - If the user has recently requested a password reset, returns a throttling error.

    POST:
    - Takes uid, token, and new password in the request data.
    - Verifies the token and resets the password if valid.
    - If the token is invalid or expired, returns an error.
    - If the request data is incomplete, returns a validation error.
    """
    permission_classes = (
        drf_permissions.AllowAny,
    )
    serializer_class = UserResetPasswordSerializer
    view_category = 'users'
    view_name = 'request-reset-password'
    throttle_classes = (NonCookieAuthThrottle, BurstRateThrottle, RootAnonThrottle, SendEmailThrottle)

    def get(self, request, *args, **kwargs):
        email = request.query_params.get('email', None)
        if not email:
            raise ValidationError('Request must include email in query params.')

        institutional = bool(request.query_params.get('institutional', None))
        mail_template = mails.FORGOT_PASSWORD if not institutional else mails.FORGOT_PASSWORD_INSTITUTION

        status_message = language.RESET_PASSWORD_SUCCESS_STATUS_MESSAGE.format(email=email)
        kind = 'success'
        # check if the user exists
        user_obj = get_user(email=email)

        if user_obj:
            # rate limit forgot_password_post
            if not throttle_period_expired(user_obj.email_last_sent, settings.SEND_EMAIL_THROTTLE):
                status_message = 'You have recently requested to change your password. Please wait a few minutes ' \
                                 'before trying again.'
                kind = 'error'
                return Response({'message': status_message, 'kind': kind}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            elif user_obj.is_active:
                # new random verification key (v2)
                user_obj.verification_key_v2 = generate_verification_key(verification_type='password')
                user_obj.email_last_sent = timezone.now()
                user_obj.save()
                reset_link = f'{settings.RESET_PASSWORD_URL}{user_obj._id}/{user_obj.verification_key_v2['token']}/'
                mails.send_mail(
                    to_addr=email,
                    mail=mail_template,
                    reset_link=reset_link,
                    can_change_preferences=False,
                )
        return Response(status=status.HTTP_200_OK, data={'message': status_message, 'kind': kind, 'institutional': institutional})

    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = request.data.get('uid', None)
        token = request.data.get('token', None)
        password = request.data.get('password', None)
        if not (uid and token and password):
            error_data = {
                'message_short': 'Invalid Request.',
                'message_long': 'The request must include uid, token, and password.',
            }
            return JsonResponse(
                error_data,
                status=status.HTTP_400_BAD_REQUEST,
                content_type='application/vnd.api+json; application/json',
            )

        user_obj = OSFUser.load(uid)
        if not (user_obj and user_obj.verify_password_token(token=token)):
            error_data = {
                'message_short': 'Invalid Request.',
                'message_long': 'The requested URL is invalid, has expired, or was already used',
            }
            return JsonResponse(
                error_data,
                status=status.HTTP_400_BAD_REQUEST,
                content_type='application/vnd.api+json; application/json',
            )

        else:
            # clear verification key (v2)
            user_obj.verification_key_v2 = {}
            # new verification key (v1) for CAS
            user_obj.verification_key = generate_verification_key(verification_type=None)
            try:
                user_obj.set_password(password)
                osf4m_source_tag, created = Tag.all_tags.get_or_create(name=CampaignSourceTags.Osf4m.value, system=True)
                osf4m_claimed_tag, created = Tag.all_tags.get_or_create(name=CampaignClaimedTags.Osf4m.value, system=True)
                if user_obj.all_tags.filter(id=osf4m_source_tag.id, system=True).exists():
                    user_obj.add_system_tag(osf4m_claimed_tag)
                user_obj.save()
            except exceptions.ChangePasswordError as error:
                return JsonResponse(
                    {'errors': [{'detail': message} for message in error.messages]},
                    status=400,
                    content_type='application/vnd.api+json; application/json',
                )

        return Response(
            status=status.HTTP_200_OK,
            content_type='application/vnd.api+json; application/json',
        )


class UserSettings(JSONAPIBaseView, generics.RetrieveUpdateAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CurrentUser,
    )

    required_read_scopes = [CoreScopes.USER_SETTINGS_READ]
    required_write_scopes = [CoreScopes.USER_SETTINGS_WRITE]
    throttle_classes = (SendEmailDeactivationThrottle,)

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

        record_referent, _ = Guid.load_referent(record_id)
        if not record_referent:
            raise NotFound('Unable to find specified record.')

        try:
            unclaimed_record = claimed_user.unclaimed_records[record_referent._id]
        except KeyError:
            if isinstance(
                record_referent,
                Preprint,
            ) and record_referent.node and record_referent.node._id in claimed_user.unclaimed_records:
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


class ConfirmEmailView(generics.CreateAPIView):
    """
    Confirm an e-mail address created during *first-time* OAuth login.

    **URL:**  POST /v2/users/<user_id>/confirm/

    **Body (JSON):**
    {
        "uid": "<osf_user_id>",
        "token": "<email_verification_token>",
        "destination": "<campaign-code or relative URL>"
    }

    On success returns a response with a 201 status code with a JSONAPI payload that includes the `redirect_url`
    attritbute.
    """
    permission_classes = (
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.USERS_CONFIRM]
    required_write_scopes = [CoreScopes.USERS_CONFIRM]

    view_category = 'users'
    view_name = 'confirm-user'

    serializer_class = ConfirmEmailTokenSerializer

    def _process_external_identity(self, user, external_identity, service_url):
        """Handle all external_identity logic, including task enqueueing and url updates."""

        provider = next(iter(external_identity))
        if provider not in user.external_identity:
            raise ValidationError('External-ID provider mismatch.')

        provider_id = next(iter(external_identity[provider]))
        ensure_external_identity_uniqueness(provider, provider_id, user)
        external_status = user.external_identity[provider][provider_id]
        user.external_identity[provider][provider_id] = 'VERIFIED'

        if external_status == 'CREATE':
            service_url += '&' + urlencode({'new': 'true'})
        elif external_status == 'LINK':
            mails.send_mail(
                user=user,
                to_addr=user.username,
                mail=mails.EXTERNAL_LOGIN_LINK_SUCCESS,
                external_id_provider=provider,
                can_change_preferences=False,
            )

        enqueue_task(update_affiliation_for_orcid_sso_users.s(user._id, provider_id))

        return service_url

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']

        user = OSFUser.load(uid)
        if not user:
            raise ValidationError('User not found.')

        verification = user.email_verifications.get(token)
        if not verification:
            raise ValidationError('Invalid or expired token.')

        external_identity = verification.get('external_identity')
        service_url = self.request.build_absolute_uri()

        if external_identity:
            service_url = self._process_external_identity(
                user,
                external_identity,
                service_url,
            )

        email = verification['email']
        if not user.is_registered:
            user.register(email)

        if not user.emails.filter(address=email.lower()).exists():
            try:
                user.emails.create(address=email.lower())
            except IntegrityError:
                raise ValidationError('Email address already exists.')

        user.date_last_logged_in = timezone.now()

        del user.email_verifications[token]
        user.verification_key = generate_verification_key()
        user.save()

        serializer.validated_data['redirect_url'] = service_url
        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED,
        )


class SanctionResponseView(generics.CreateAPIView, UserMixin):
    """
    **URL:**  POST /v2/users/<user_id>/sanction_response/

    **Body (JSON):**
    {
        "uid": "<osf_user_id>",
        "token": "<email_verification_token>",
        "destination": "<campaign-code or relative URL>"
    }

    On success the endpoint returns (HTTP 200)
    """
    permission_classes = (
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.SANCTION_RESPONSE]

    view_category = 'users'
    view_name = 'sanction-response'

    serializer_class = SanctionTokenSerializer

    def perform_create(self, serializer):
        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        action = serializer.validated_data['action']
        if not action:
            raise ValidationError('`approve` or `reject` action not found.')
        sanction_type = serializer.validated_data.get('sanction_type')
        if not sanction_type:
            raise ValidationError('sanction_type not found.')

        if self.get_user() != OSFUser.load(uid):
            raise ValidationError('User not found.')

        token_handler = TokenHandler.from_string(token)

        sanction_handler(
            sanction_type,
            action,
            payload=token_handler.payload,
            encoded_token=token_handler.encoded_token,
            user=self.get_user(),
        )


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
                    send_confirm_email_async(user, email=address, renew=True)
                    user.email_last_sent = timezone.now()
                    user.save()

        return UserEmail(email_id=email_id, address=address, confirmed=confirmed, verified=verified, primary=primary, is_merge=is_merge)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
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


class UserMessageView(JSONAPIBaseView, generics.CreateAPIView):
    """
    List and create UserMessages for a user.
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        UserMessagePermissions,
    )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.USERS_MESSAGE_WRITE_EMAIL]
    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON)
    throttle_classes = [BurstRateThrottle, SendEmailThrottle]
    serializer_class = UserMessageSerializer

    view_category = 'users'
    view_name = 'user-messages'


class ExternalLoginConfirmEmailView(generics.CreateAPIView):
    permission_classes = (
        drf_permissions.AllowAny,
    )
    serializer_class = ConfirmEmailTokenSerializer
    view_category = 'users'
    view_name = 'external-login-confirm-email'
    throttle_classes = (NonCookieAuthThrottle, BurstRateThrottle, RootAnonThrottle)

    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = request.data.get('uid', None)
        token = request.data.get('token', None)
        destination = request.data.get('destination', None)

        user = OSFUser.load(uid)
        if not user:
            sentry.log_message('external_login_confirm_email_get::400 - Cannot find user')
            raise ValidationError('User not found.')

        if not destination:
            sentry.log_message('external_login_confirm_email_get::400 - bad destination')
            raise ValidationError('Bad destination.')

        if token not in user.email_verifications:
            sentry.log_message('external_login_confirm_email_get::400 - bad token')
            raise ValidationError('Invalid token.')

        verification = user.email_verifications[token]
        email = verification['email']
        provider = list(verification['external_identity'].keys())[0]
        provider_id = list(verification['external_identity'][provider].keys())[0]

        if provider not in user.external_identity:
            sentry.log_message('external_login_confirm_email_get::400 - Auth error...wrong provider')
            raise ValidationError('Wrong provider.')

        external_status = user.external_identity[provider][provider_id]

        try:
            ensure_external_identity_uniqueness(provider, provider_id, user)
        except ValidationError as e:
            sentry.log_message('external_login_confirm_email_get::403 - Validation Error')
            raise ValidationError(str(e))

        if not user.is_registered:
            user.register(email)

        if not user.emails.filter(address=email.lower()).exists():
            user.emails.create(address=email.lower())

        user.date_last_logged_in = timezone.now()
        user.external_identity[provider][provider_id] = 'VERIFIED'
        user.social[provider.lower()] = provider_id
        del user.email_verifications[token]
        user.verification_key = generate_verification_key()
        user.save()

        service_url = request.build_absolute_uri()

        if external_status == 'CREATE':
            service_url += '&{}'.format(urlencode({'new': 'true'}))
        elif external_status == 'LINK':
            mails.send_mail(
                user=user,
                to_addr=user.username,
                mail=mails.EXTERNAL_LOGIN_LINK_SUCCESS,
                external_id_provider=provider,
                can_change_preferences=False,
            )

        enqueue_task(update_affiliation_for_orcid_sso_users.s(user._id, provider_id))

        return Response(status=status.HTTP_200_OK)
