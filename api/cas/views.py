import json

from rest_framework import generics
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from rest_framework.response import Response

from api.base.views import JSONAPIBaseView
from api.cas import util, messages
from api.cas.auth import CasJweAuthentication
from api.cas.permissions import IsCasJweAuthentication

from framework.auth.oauth_scopes import CoreScopes

from osf.models import ApiOAuth2Application, ApiOAuth2PersonalToken, ApiOAuth2Scope, Institution, OSFUser

from website import settings as web_settings


class AuthLogin(JSONAPIBaseView, generics.CreateAPIView):
    """ Default osf login.
    """

    view_category = 'cas'
    view_name = 'auth-login'
    permission_classes = (IsCasJweAuthentication,)
    authentication_classes = (CasJweAuthentication,)
    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    def post(self, request, *args, **kwargs):

        # The response `data` payload is expected in the following structures
        # {
        #     'userId': <the user's GUID>
        #     'attributes': {
        #         'username': 'testuser@fakecos.io',
        #         'givenName': 'User',
        #         'familyName': 'Test',
        #     },
        # }
        content = {
            'userId': request.user._id,
            'attributes': {
                'username': request.user.username,
                'givenName': request.user.given_name,
                'familyName': request.user.family_name,
            }
        }
        return Response(content)


class AuthRegister(JSONAPIBaseView, generics.CreateAPIView):
    """ Default osf account creation.
    """

    view_category = 'cas'
    view_name = 'auth-register'
    permission_classes = (IsCasJweAuthentication,)
    authentication_classes = (CasJweAuthentication,)
    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthInstitution(JSONAPIBaseView, generics.CreateAPIView):
    """ Institution login.
    """

    view_category = 'cas'
    view_name = 'auth-institution'
    permission_classes = (IsCasJweAuthentication,)
    authentication_classes = (CasJweAuthentication,)
    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthVerifyEmail(JSONAPIBaseView, generics.CreateAPIView):
    """ Verify the primary email for a new osf account.
    """

    view_category = 'cas'
    view_name = 'auth-verify-email'
    permission_classes = (IsCasJweAuthentication,)
    authentication_classes = (CasJweAuthentication,)
    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    def post(self, request, *args, **kwargs):

        content = {
            "verificationKey": request.user.verification_key,
            "serviceUrl": web_settings.DOMAIN + 'cas/action/' + request.user._id + '/',
        }
        return Response(data=content, status=status.HTTP_200_OK)


class AuthResetPassword(JSONAPIBaseView, generics.CreateAPIView):
    """ Reset the password for an osf account.
    """

    view_category = 'cas'
    view_name = 'auth-reset-password'
    permission_classes = (IsCasJweAuthentication,)
    authentication_classes = (CasJweAuthentication,)
    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    def post(self, request, *args, **kwargs):

        content = {
            "verificationKey": request.user.verification_key,
            "serviceUrl": web_settings.DOMAIN + 'cas/action/' + request.user._id + '/',
        }
        return Response(data=content, status=status.HTTP_200_OK)


class ServiceFindAccount(JSONAPIBaseView, generics.CreateAPIView):
    """ Find user's account by email. If relevant pending action exists, send verification email.
    """

    view_category = 'cas'
    view_name = 'service-find-account'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        service_type = data.get('type')
        if not service_type:
            raise ValidationError(detail=messages.INVALID_REQUEST)

        user = None
        error_message = None

        if service_type == 'FIND_ACCOUNT_FOR_VERIFY_EMAIL':
            user, error_message = util.find_account_for_verify_email(data.get('user'))

        if service_type == 'FIND_ACCOUNT_FOR_RESET_PASSWORD':
            user, error_message = util.find_account_for_reset_password(data.get('user'))

        if not user and error_message:
            raise PermissionDenied(detail=error_message)

        if user and not error_message:
            return Response(status=status.HTTP_204_NO_CONTENT)

        raise APIException(detail=messages.REQUEST_FAILED)


class ServiceCheckPersonalAccessToken(JSONAPIBaseView, generics.CreateAPIView):
    """ Get the owner and scopes of a personal access token by token id.
    """

    view_category = 'cas'
    view_name = 'service-check-personal-access-token'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        token_id = data.get('tokenId')
        if not token_id:
            raise ValidationError(detail=messages.INVALID_REQUEST)

        try:
            token = ApiOAuth2PersonalToken.objects.get(token_id=token_id)
        except ApiOAuth2PersonalToken.DoesNotExist:
            raise PermissionDenied(detail=messages.TOKEN_NOT_FOUND)

        try:
            user = OSFUser.objects.get(pk=token.owner_id)
        except OSFUser.DoesNotExist:
            raise PermissionDenied(detail=messages.TOKEN_OWNER_NOT_FOUND)

        content = {
            'tokenId': token.token_id,
            'ownerId': user._id,
            'tokenScopes': token.scopes,
        }

        return Response(content)


class ServiceCheckOauthScope(JSONAPIBaseView, generics.CreateAPIView):
    """ Get the description of an oauth scope by scope name.
    """

    view_category = 'cas'
    view_name = 'service-check-oauth-scope'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        scope_name = data.get('scopeName')
        if not scope_name:
            raise ValidationError(detail=messages.INVALID_REQUEST)

        try:
            scope = ApiOAuth2Scope.objects.get(name=scope_name)
            if not scope.is_active:
                raise PermissionDenied(detail=messages.SCOPE_NOT_ACTIVE)
        except ApiOAuth2Scope.DoesNotExist:
            raise PermissionDenied(detail=messages.SCOPE_NOT_FOUND)

        content = {
            'scopeDescription': scope.description,
        }

        return Response(content)


class ServiceLoadDeveloperApps(JSONAPIBaseView, generics.CreateAPIView):
    """ Load all active developer applications.
    """

    view_category = 'cas'
    view_name = 'service-load-developer-apps'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        service_type = data.get('serviceType')
        if not service_type or service_type != 'LOAD_DEVELOPER_APPS':
            raise ValidationError(detail=messages.INVALID_REQUEST)

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
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        service_type = data.get('serviceType')
        if not service_type or service_type != 'LOAD_INSTITUTIONS':
            raise ValidationError(detail=messages.INVALID_REQUEST)

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
