from rest_framework import status
from rest_framework.response import Response

from api.base.views import JSONAPIBaseView
from api.cas import account, login, service, util


class APICASView(JSONAPIBaseView):
    """ JSON API CAS View.
    """

    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None


class LoginOSF(APICASView):
    """ Default login through OSF.
    """
    view_name = 'login-osf'

    def post(self, request):

        data = util.load_request_body_data(request)
        user = login.osf_login(data.get('user', None))

        content = {
            'userId': user._id,
            'attributes': {
                'username': user.username,
                'givenName': user.given_name,
                'familyName': user.family_name,
            }
        }

        return Response(data=content, status=status.HTTP_200_OK)


class LoginInstitution(APICASView):
    """ Login through institutions.
    """

    view_name = 'login-institution'

    def post(self, request):

        data = util.load_request_body_data(request)
        login.institution_login(data.get('provider', None))

        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginExternal(APICASView):
    """ Login through non-institution external IdP.
    """

    view_name = 'login-external'

    def post(self, request):

        data = util.load_request_body_data(request)
        user = login.external_login(data.get('user', None))

        content = {
            'username': user.username
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountRegisterOSF(APICASView):
    """ Default account creation through OSF.
    """

    view_name = 'account-register-osf'

    def post(self, request):

        data = util.load_request_body_data(request)
        account.create_unregistered_user(data.get('user', None))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountVerifyOSF(APICASView):
    """ Verify email for account creation through OSF.
    """

    view_name = 'account-verify-osf'

    def post(self, request):

        data = util.load_request_body_data(request)
        user = account.register_user(data.get('user', None))

        content = {
            'verificationKey': user.verification_key,
            'userId': user._id,
            'username': user.username,
            'casAction': 'account-verify-osf',
            'nextUrl': False,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountVerifyOSFResend(APICASView):
    """ Find user by email and resend verification email for account creation.
    """

    view_name = 'account-verify-osf-resend'

    def post(self, request):

        data = util.load_request_body_data(request)
        account.resend_confirmation(data.get('user', None))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountRegisterExternal(APICASView):
    """ Account creation (or link) though non-institution external identity provider.
    """

    view_name = 'account-register-external'

    def post(self, request):

        data = util.load_request_body_data(request)
        user, create_or_link = account.create_or_link_external_user(data.get('user', None))

        content = {
            'username': user.username,
            'createOrLink': create_or_link,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountVerifyExternal(APICASView):
    """ Verify email for account creation (or link) though non-institution external identity provider.
    """

    view_name = 'account-verify-external'

    def post(self, request):

        data = util.load_request_body_data(request)
        user, create_or_link = account.register_external_user(data.get('user', None))

        content = {
            'verificationKey': user.verification_key,
            'userId': user._id,
            'username': user.username,
            'casAction': 'account-verify-external',
            'nextUrl': True,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountPasswordForgot(APICASView):
    """ Find user by email and (re)send verification email for password reset.
    """

    view_name = 'account-password-forgot'

    def post(self, request):

        data = util.load_request_body_data(request)
        account.send_password_reset_email(data.get('user', None))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountPasswordReset(APICASView):
    """ Reset the password for an eligible OSF account.
    """

    view_name = 'account-password-reset'

    def post(self, request):

        data = util.load_request_body_data(request)
        user = account.reset_password(data.get('user', None))

        content = {
            'verificationKey': user.verification_key,
            'userId': user._id,
            'username': user.username,
            'casAction': 'account-password-meetings' if data.get('meetings') else 'account-password-reset',
            'nextUrl': False,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class ServiceOauthToken(APICASView):
    """ Return the owner and scopes of a personal access token by token id.
    """

    view_name = 'service-oauth-token'

    def post(self, request):

        data = util.load_request_body_data(request)
        content = service.get_oauth_token(data)
        return Response(data=content, status=status.HTTP_200_OK)


class ServiceOauthScope(APICASView):
    """ Return the description of the oauth scope by scope name.
    """

    view_name = 'service-oauth-scope'

    def post(self, request):

        data = util.load_request_body_data(request)
        content = service.get_oauth_scope(data)
        return Response(data=content, status=status.HTTP_200_OK)


class ServiceOauthApps(APICASView):
    """ Load all active developer applications.
    """

    view_name = 'service-oauth-apps'

    def post(self, request):

        util.load_request_body_data(request)
        content = service.load_oauth_apps()
        return Response(data=content, status=status.HTTP_200_OK)


class ServiceInstitutions(APICASView):
    """ Load institutions that provide authentication delegation.
    """

    view_name = 'service-institutions'

    def post(self, request):

        util.load_request_body_data(request)
        content = service.load_institutions()
        return Response(data=content, status=status.HTTP_200_OK)
