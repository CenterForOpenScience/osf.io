import json

from rest_framework import generics
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response

from api.base.views import JSONAPIBaseView
from api.cas import messages
from api.cas import login, account, permissions

from osf.models import ApiOAuth2Application, ApiOAuth2PersonalToken, ApiOAuth2Scope, Institution, OSFUser

from website import settings as web_settings


class LoginOsf(JSONAPIBaseView, generics.CreateAPIView):
    """ Default login through OSF.
    """

    view_category = 'cas'
    view_name = 'login-osf'
    permission_classes = (permissions.IsCasLogin,)
    authentication_classes = (login.CasLoginAuthentication,)

    def post(self, request, *args, **kwargs):

        content = {
            'userId': request.user._id,
            'attributes': {
                'username': request.user.username,
                'givenName': request.user.given_name,
                'familyName': request.user.family_name,
            }
        }

        return Response(data=content, status=status.HTTP_200_OK)


class LoginInstitution(JSONAPIBaseView, generics.CreateAPIView):
    """ Login through institutions.
    """

    view_category = 'cas'
    view_name = 'login-institution'
    permission_classes = (permissions.IsCasLogin,)
    authentication_classes = (login.CasLoginAuthentication,)

    def post(self, request, *args, **kwargs):

        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginExternal(JSONAPIBaseView, generics.CreateAPIView):
    """ Login through non-institution external IdP.
    """

    view_category = 'cas'
    view_name = 'login-external'
    permission_classes = (permissions.IsCasLogin,)
    authentication_classes = (login.CasLoginAuthentication,)

    def post(self, request, *args, **kwargs):

        content = {
            "username": request.user.username
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountRegisterOsf(JSONAPIBaseView, generics.CreateAPIView):
    """ Default account creation through OSF.
    """

    view_category = 'cas'
    view_name = 'account-register-osf'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = json.loads(request.body['data'])
        account_action = body_data.get('accountAction')

        if account_action != "REGISTER_OSF":
            raise ValidationError(detail=messages.INVALID_REQUEST)

        account.handle_register_osf(body_data.get('user'))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountVerifyOsf(JSONAPIBaseView, generics.CreateAPIView):
    """ Verify email for account creation through OSF.
    """

    view_category = 'cas'
    view_name = 'account-verify-osf'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = json.loads(request.body['data'])
        account_action = body_data.get('accountAction')

        if account_action != "VERIFY_OSF":
            raise ValidationError(detail=messages.INVALID_REQUEST)

        user = account.handle_verify_osf(body_data.get('user'))

        content = {
            'verificationKey': user.verification_key,
            'casActionUrl': web_settings.DOMAIN + 'cas/action/' + user._id + '/',
            'destinationView': 'index',
            'campaign': True
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountVerifyOsfResend(JSONAPIBaseView, generics.CreateAPIView):
    """ Find user by email and resend verification email for account creation.
    """

    view_category = 'cas'
    view_name = 'account-verify-osf-resend'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = json.loads(request.body['data'])
        account_action = body_data.get('accountAction')

        if account_action != 'VERIFY_OSF_RESEND':
            raise ValidationError(detail=messages.INVALID_REQUEST)

        account.handle_verify_osf_resend(body_data.get('user'))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountRegisterExternal(JSONAPIBaseView, generics.CreateAPIView):
    """ Account creation (or link) though non-institution external identity provider.
    """

    view_category = 'cas'
    view_name = 'account-register-external'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = json.loads(request.body['data'])
        account_action = body_data.get('accountAction')

        if account_action != 'REGISTER_EXTERNAL':
            raise ValidationError(detail=messages.INVALID_REQUEST)

        user, create_or_link = account.handle_register_external(body_data.get('user'))

        content = {
            'username': user.username,
            'createOrLink': create_or_link,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountVerifyExternal(JSONAPIBaseView, generics.CreateAPIView):
    """ Verify email for account creation (or link) though non-institution external identity provider.
    """

    view_category = 'cas'
    view_name = 'account-verify-external'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = json.loads(request.body['data'])
        account_action = body_data.get('accountAction')

        if account_action != 'VERIFY_EXTERNAL':
            raise ValidationError(detail=messages.INVALID_REQUEST)

        user, create_or_link = account.handle_verify_external(body_data.get('user'))

        content = {
            'verificationKey': user.verification_key,
            'casActionUrl': web_settings.DOMAIN + 'cas/action/' + user._id + '/',
            'destinationView': 'index',
            'campaign': True
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountPasswordForgot(JSONAPIBaseView, generics.CreateAPIView):
    """ Find user by email and (re)send verification email for password reset.
    """

    view_category = 'cas'
    view_name = 'account-password-forgot'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = json.loads(request.body['data'])
        account_action = body_data.get('accountAction')

        if account_action != 'PASSWORD_FORGOT':
            raise ValidationError(detail=messages.INVALID_REQUEST)

        account.handle_password_forgot(body_data.get('data'))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountPasswordReset(JSONAPIBaseView, generics.CreateAPIView):
    """ Reset the password for an osf account.
    """

    view_category = 'cas'
    view_name = 'account-password-reset'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = json.loads(request.body['data'])
        account_action = body_data.get('accountAction')

        if account_action != 'PASSWORD_RESET':
            raise ValidationError(detail=messages.INVALID_REQUEST)

        user = account.handle_password_reset(body_data.get('user'))

        content = {
            "verificationKey": user.verification_key,
            'casActionUrl': web_settings.DOMAIN + 'cas/action/' + request.user._id + '/',
            'destinationView': 'user-account',
            'campaign': False
        }

        return Response(data=content, status=status.HTTP_200_OK)


class ServiceOauthToken(JSONAPIBaseView, generics.CreateAPIView):
    """ Get the owner and scopes of a personal access token by token id.
    """

    view_category = 'cas'
    view_name = 'service-oauth-token'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        data = json.loads(request.body['data'])
        service_type = data.get('serviceType')
        token_id = data.get('tokenId')

        if service_type != 'OAUTH_TOKEN' or not token_id:
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


class ServiceOauthScope(JSONAPIBaseView, generics.CreateAPIView):
    """ Get the description of the oauth scope by scope name.
    """

    view_category = 'cas'
    view_name = 'service-oauth-scope'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        data = json.loads(request.body['data'])
        service_type = data.get('serviceType')
        scope_name = data.get('scopeName')

        if service_type != 'OAUTH_SCOPE' or not scope_name:
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


class ServiceOauthApps(JSONAPIBaseView, generics.CreateAPIView):
    """ Load all active developer applications.
    """

    view_category = 'cas'
    view_name = 'service-oauth-apps'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        data = json.loads(request.body['data'])
        service_type = data.get('serviceType')

        if service_type != 'OAUTH_APPS':
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


class ServiceInstitutions(JSONAPIBaseView, generics.CreateAPIView):
    """ Load institutions that provide authentication delegation. 
    """

    view_category = 'cas'
    view_name = 'service-institutions'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        data = json.loads(request.body['data'])
        service_type = data.get('serviceType')

        if service_type != 'INSTITUTIONS':
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
