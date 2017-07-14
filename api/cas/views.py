import json

from rest_framework import generics
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.base.views import JSONAPIBaseView
from api.cas import login, account, messages, permissions, service
from api.cas.mixins import APICASMixin


class LoginOsf(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Default login through OSF. Authentication Required.
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


class LoginInstitution(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Login through institutions. Authentication Required.
    """

    view_category = 'cas'
    view_name = 'login-institution'
    permission_classes = (permissions.IsCasLogin,)
    authentication_classes = (login.CasLoginAuthentication,)

    def post(self, request, *args, **kwargs):

        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginExternal(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Login through non-institution external IdP. Authentication Required.
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


class AccountRegisterOsf(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Default account creation through OSF.
    """

    view_category = 'cas'
    view_name = 'account-register-osf'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        self.load_request_body_data(request)
        body_data = json.loads(request.body['data'])
        account_action = body_data.get('accountAction')

        if account_action != "REGISTER_OSF":
            raise ValidationError(detail=messages.INVALID_REQUEST)

        account.handle_register_osf(body_data.get('user'))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountVerifyOsf(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Verify email for account creation through OSF.
    """

    view_category = 'cas'
    view_name = 'account-verify-osf'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = self.load_request_body_data(request)
        account_action = body_data.get('accountAction')

        if account_action != "VERIFY_OSF":
            raise ValidationError(detail=messages.INVALID_REQUEST)

        user = account.handle_verify_osf(body_data.get('user'))

        content = {
            "verificationKey": user.verification_key,
            'userId': user._id,
            'casAction': 'account-verify-osf',
            'nextUrl': False,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountVerifyOsfResend(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Find user by email and resend verification email for account creation.
    """

    view_category = 'cas'
    view_name = 'account-verify-osf-resend'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = self.load_request_body_data(request)
        account_action = body_data.get('accountAction')

        if account_action != 'VERIFY_OSF_RESEND':
            raise ValidationError(detail=messages.INVALID_REQUEST)

        account.handle_verify_osf_resend(body_data.get('user'))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountRegisterExternal(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Account creation (or link) though non-institution external identity provider.
    """

    view_category = 'cas'
    view_name = 'account-register-external'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = self.load_request_body_data(request)
        account_action = body_data.get('accountAction')

        if account_action != 'REGISTER_EXTERNAL':
            raise ValidationError(detail=messages.INVALID_REQUEST)

        user, create_or_link = account.handle_register_external(body_data.get('user'))

        content = {
            'username': user.username,
            'createOrLink': create_or_link,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountVerifyExternal(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Verify email for account creation (or link) though non-institution external identity provider.
    """

    view_category = 'cas'
    view_name = 'account-verify-external'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = self.load_request_body_data(request)
        account_action = body_data.get('accountAction')

        if account_action != 'VERIFY_EXTERNAL':
            raise ValidationError(detail=messages.INVALID_REQUEST)

        user, create_or_link = account.handle_verify_external(body_data.get('user'))

        content = {
            "verificationKey": user.verification_key,
            'userId': user._id,
            'casAction': 'account-verify-external',
            'nextUrl': True,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountPasswordForgot(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Find user by email and (re)send verification email for password reset.
    """

    view_category = 'cas'
    view_name = 'account-password-forgot'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = self.load_request_body_data(request)
        account_action = body_data.get('accountAction')

        if account_action != 'PASSWORD_FORGOT':
            raise ValidationError(detail=messages.INVALID_REQUEST)

        account.handle_password_forgot(body_data.get('user'))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountPasswordReset(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Reset the password for an osf account.
    """

    view_category = 'cas'
    view_name = 'account-password-reset'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = self.load_request_body_data(request)
        account_action = body_data.get('accountAction')

        if account_action != 'PASSWORD_RESET':
            raise ValidationError(detail=messages.INVALID_REQUEST)

        user = account.handle_password_reset(body_data.get('user'))

        content = {
            "verificationKey": user.verification_key,
            'userId': user._id,
            'casAction': 'account-password-reset',
            'nextUrl': False,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class ServiceOauthToken(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Get the owner and scopes of a personal access token by token id.
    """

    view_category = 'cas'
    view_name = 'service-oauth-token'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = self.load_request_body_data(request)
        content = service.get_oauth_token(body_data)
        return Response(data=content, status=status.HTTP_200_OK)


class ServiceOauthScope(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Get the description of the oauth scope by scope name.
    """

    view_category = 'cas'
    view_name = 'service-oauth-scope'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = self.load_request_body_data(request)
        content = service.get_oauth_scope(body_data)
        return Response(data=content, status=status.HTTP_200_OK)


class ServiceOauthApps(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Load all active developer applications.
    """

    view_category = 'cas'
    view_name = 'service-oauth-apps'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = self.load_request_body_data(request)
        content = service.load_oauth_apps(body_data)
        return Response(data=content, status=status.HTTP_200_OK)


class ServiceInstitutions(APICASMixin, generics.CreateAPIView, JSONAPIBaseView):
    """ Load institutions that provide authentication delegation. 
    """

    view_category = 'cas'
    view_name = 'service-institutions'
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        body_data = self.load_request_body_data(request)
        content = service.load_institutions(body_data)
        return Response(data=content, status=status.HTTP_200_OK)
