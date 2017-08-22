from rest_framework import status
from rest_framework.response import Response

from api.base.views import JSONAPIBaseView
from api.cas import account, login, service, util


class LoginOSF(JSONAPIBaseView):
    """ Default login through OSF.
    """
    view_name = 'login-osf'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

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


class LoginInstitution(JSONAPIBaseView):
    """ Login through institutions.
    """

    view_name = 'login-institution'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        data = util.load_request_body_data(request)
        login.institution_login(data.get('provider', None))

        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginExternal(JSONAPIBaseView):
    """ Login through non-institution external IdP.
    """

    view_name = 'login-external'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        data = util.load_request_body_data(request)
        user = login.external_login(data.get('user', None))

        content = {
            'username': user.username
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountRegisterOSF(JSONAPIBaseView):
    """ Default account creation through OSF.
    """

    view_name = 'account-register-osf'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        data = util.load_request_body_data(request)
        account.create_unregistered_user(data.get('user', None))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountVerifyOSF(JSONAPIBaseView):
    """ Verify email for account creation through OSF.
    """

    view_name = 'account-verify-osf'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

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


class AccountVerifyOSFResend(JSONAPIBaseView):
    """ Find user by email and resend verification email for account creation.
    """

    view_name = 'account-verify-osf-resend'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        data = util.load_request_body_data(request)
        account.resend_confirmation(data.get('user', None))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountRegisterExternal(JSONAPIBaseView):
    """ Account creation (or link) though non-institution external identity provider.
    """

    view_name = 'account-register-external'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        data = util.load_request_body_data(request)
        user, create_or_link = account.create_or_link_external_user(data.get('user', None))

        content = {
            'username': user.username,
            'createOrLink': create_or_link,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountVerifyExternal(JSONAPIBaseView):
    """ Verify email for account creation (or link) though non-institution external identity provider.
    """

    view_name = 'account-verify-external'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        data = util.load_request_body_data(request)
        user, created_or_linked = account.register_external_user(data.get('user', None))

        content = {
            'verificationKey': user.verification_key,
            'userId': user._id,
            'username': user.username,
            'createdOrLinked': created_or_linked,
            'casAction': 'account-verify-external',
            'nextUrl': True,
        }

        return Response(data=content, status=status.HTTP_200_OK)


class AccountPasswordForgot(JSONAPIBaseView):
    """ Find user by email and (re)send verification email for password reset.
    """

    view_name = 'account-password-forgot'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        data = util.load_request_body_data(request)
        account.send_password_reset_email(data.get('user', None))

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountPasswordReset(JSONAPIBaseView):
    """ Reset the password for an eligible OSF account.
    """

    view_name = 'account-password-reset'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

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


class ServiceOauthToken(JSONAPIBaseView):
    """ Return the owner and scopes of a personal access token by token id.
    """

    view_name = 'service-oauth-token'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        data = util.load_request_body_data(request)
        content = service.get_oauth_token(data)
        return Response(data=content, status=status.HTTP_200_OK)


class ServiceOauthScope(JSONAPIBaseView):
    """ Return the description of the oauth scope by scope name.
    """

    view_name = 'service-oauth-scope'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        data = util.load_request_body_data(request)
        content = service.get_oauth_scope(data)
        return Response(data=content, status=status.HTTP_200_OK)


class ServiceOauthApps(JSONAPIBaseView):
    """ Load all active developer applications.
    """

    view_name = 'service-oauth-apps'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        util.load_request_body_data(request)
        content = service.load_oauth_apps()
        return Response(data=content, status=status.HTTP_200_OK)


class ServiceInstitutions(JSONAPIBaseView):
    """ Load institutions that provide authentication delegation.
    """

    view_name = 'service-institutions'
    view_category = 'cas'
    authentication_classes = ()
    permission_classes = ()
    serializer_class = None

    def post(self, request, *args, **kwargs):

        util.load_request_body_data(request)
        content = service.load_institutions()
        return Response(data=content, status=status.HTTP_200_OK)
