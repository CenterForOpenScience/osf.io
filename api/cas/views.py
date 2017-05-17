import json

from django.contrib.auth.models import AnonymousUser

from rest_framework import generics
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response

from api.base.serializers import JSONAPISerializer
from api.base.views import JSONAPIBaseView
from api.cas import util
from api.cas.auth import CasAuthentication
from api.cas.permissions import IsCasAuthentication

from framework.auth.oauth_scopes import CoreScopes

from osf.models import ApiOAuth2Application, ApiOAuth2PersonalToken, ApiOAuth2Scope, Institution, OSFUser


class AuthLogin(JSONAPIBaseView, generics.CreateAPIView):
    """ Default osf login.
    """

    permission_classes = (IsCasAuthentication, )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'cas'
    view_name = 'auth-login'

    serializer_class = JSONAPISerializer

    authentication_classes = (CasAuthentication, )

    def post(self, request, *args, **kwargs):

        user = request.user
        if not user or isinstance(user, AnonymousUser):
            raise AuthenticationFailed

        # The response `data` payload is expected in the following structures
        # {
        #     'status': 'AUTHENTICATION SUCCESS',
        #     'userId': <the user's GUID>
        #     'attributes': {
        #         'username': 'testuser@fakecos.io',
        #         'givenName': 'User',
        #         'familyName': 'Test',
        #     },
        # }
        content = {
            'status': 'AUTHENTICATION_SUCCESS',
            'userId': user._id,
            'attributes': {
                'username': user.username,
                'givenName': user.given_name,
                'familyName': user.family_name,
            }
        }

        return Response(content)


class AuthRegister(JSONAPIBaseView, generics.CreateAPIView):
    """ Default osf account creation.
    """

    permission_classes = (IsCasAuthentication, )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'cas'
    view_name = 'auth-register'

    serializer_class = JSONAPISerializer

    authentication_classes = (CasAuthentication, )

    def post(self, request, *args, **kwargs):

        if not request.user or isinstance(request.user, AnonymousUser):
            raise AuthenticationFailed
        else:
            # The response `data` payload is expected in the following structures
            # {
            #     'status': 'REGISTRATION_SUCCESS'
            # }
            content = {
                'status': 'REGISTRATION_SUCCESS',
            }

        return Response(content)


class AuthInstitution(JSONAPIBaseView, generics.CreateAPIView):
    """ Institution login.
    """

    permission_classes = (IsCasAuthentication, )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'cas'
    view_name = 'auth-institution'

    serializer_class = JSONAPISerializer

    authentication_classes = (CasAuthentication, )

    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthVerifyEmail(JSONAPIBaseView, generics.CreateAPIView):
    """ Verify the primary email for a new osf account.
    """

    permission_classes = (IsCasAuthentication, )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'cas'
    view_name = 'auth-verify-email'

    serializer_class = JSONAPISerializer

    authentication_classes = (CasAuthentication, )

    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthResetPassword(JSONAPIBaseView, generics.CreateAPIView):
    """ Reset the password for an osf account.
    """

    permission_classes = (IsCasAuthentication, )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'cas'
    view_name = 'auth-reset-password'

    serializer_class = JSONAPISerializer

    authentication_classes = (CasAuthentication, )

    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


class UtilityFindAccount(JSONAPIBaseView, generics.CreateAPIView):
    """ Find user's account by email. If relevant pending action exists, send verification email.
    """

    view_category = 'cas'
    view_name = 'service-find-account'

    serializer_class = JSONAPISerializer
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        util_type = data.get('type')
        if not util_type:
            raise AuthenticationFailed(detail=util.INVALID_REQUEST_BODY)

        if util_type == 'FIND_ACCOUNT_FOR_VERIFY_EMAIL':
            if util.find_account_for_verify_email(data.get('user')):
                return Response(status=status.HTTP_204_NO_CONTENT)

        if util_type == 'FIND_ACCOUNT_FOR_RESET_PASSWORD':
            if util.find_account_for_reset_password(data.get('user')):
                return Response(status=status.HTTP_204_NO_CONTENT)

        raise AuthenticationFailed(detail=util.INVALID_REQUEST_BODY)


class UtilityCheckPersonalAccessToken(JSONAPIBaseView, generics.CreateAPIView):
    """ Get the owner and scopes of a personal access token by token id.
    """

    view_category = 'cas'
    view_name = 'service-check-personal-access-token'

    serializer_class = JSONAPISerializer
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        token_id = data.get('tokenId')
        if not token_id:
            raise AuthenticationFailed(detail=util.INVALID_REQUEST_BODY)

        try:
            token = ApiOAuth2PersonalToken.objects.get(token_id=token_id)
        except ApiOAuth2PersonalToken.DoesNotExist:
            raise AuthenticationFailed(detail=util.TOKEN_NOT_FOUND)

        try:
            user = OSFUser.objects.get(pk=token.owner_id)
        except OSFUser.DoesNotExist:
            raise AuthenticationFailed(detail=util.TOKEN_OWNER_NOT_FOUND)

        content = {
            'tokenId': token.token_id,
            'ownerId': user._id,
            'tokenScopes': token.scopes,
        }

        return Response(content)


class UtilityCheckOauthScope(JSONAPIBaseView, generics.CreateAPIView):
    """ Get the description of an oauth scope by scope name.
    """

    view_category = 'cas'
    view_name = 'service-get-oauth-description'

    serializer_class = JSONAPISerializer
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        scope_name = data.get('scopeName')
        if not scope_name:
            raise AuthenticationFailed(detail=util.INVALID_REQUEST_BODY)

        try:
            scope = ApiOAuth2Scope.objects.get(name=scope_name)
            if not scope.is_active:
                raise AuthenticationFailed(detail=util.SCOPE_NOT_ACTIVE)
        except ApiOAuth2Scope.DoesNotExist:
            raise AuthenticationFailed(detail=util.SCOPE_NOT_FOUND)

        content = {
            'scopeDescription': scope.description,
        }

        return Response(content)


class ServiceLoadDeveloperApps(JSONAPIBaseView, generics.CreateAPIView):
    """ Load all active developer applications.
    """

    view_category = 'cas'
    view_name = 'service-load-developer-apps'

    serializer_class = JSONAPISerializer
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        service_type = data.get('serviceType')
        if not service_type or service_type != 'LOAD_DEVELOPER_APPS':
            raise AuthenticationFailed(detail=util.INVALID_REQUEST_BODY)

        oauth_applications = ApiOAuth2Application.objects.filter(is_active=True)

        content = {}
        for oauth_app in oauth_applications:
            key = oauth_app._id
            value = {
                'name': oauth_app.name,
                'description': oauth_app.description,
                'callbackUrl': oauth_app.callback_url,
                'clientId': oauth_app.client_id,
                'clientSecret': oauth_app.client_secret,
            }
            content.update({key: value})

        return Response(content)


class ServiceLoadInstitutions(JSONAPIBaseView, generics.CreateAPIView):
    """ Load institutions that provide authentication delegation. 
    """

    view_category = 'cas'
    view_name = 'service-load-institutions'

    serializer_class = JSONAPISerializer
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        service_type = data.get('serviceType')
        if not service_type or service_type != 'LOAD_INSTITUTIONS':
            raise AuthenticationFailed(detail=util.INVALID_REQUEST_BODY)

        institutions = Institution.objects\
            .exclude(delegation_protocol__isnull=True)\
            .exclude(delegation_protocol__exact='')

        content = {}
        for institution in institutions:
            key = institution._id
            value = {
                'institutionName': institution.name,
                'institutionLoginUrl': institution.login_url if institution.login_url else '',
                'institutionLogoutUrl': institution.logout_url,
                'delegationProtocol': institution.delegation_protocol,
            }
            content.update({key: value})

        return Response(content)
