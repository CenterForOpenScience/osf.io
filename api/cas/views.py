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


class CasLogin(JSONAPIBaseView, generics.CreateAPIView):

    permission_classes = (IsCasAuthentication,)

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'cas'
    view_name = 'cas-login'

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


class CasRegister(JSONAPIBaseView, generics.CreateAPIView):

    permission_classes = (IsCasAuthentication, )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'cas'
    view_name = 'cas-login'

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


class CasInstitutionAuthenticate(JSONAPIBaseView, generics.CreateAPIView):

    permission_classes = (IsCasAuthentication, )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'cas'
    view_name = 'cas-institution-authenticate'

    serializer_class = JSONAPISerializer

    authentication_classes = (CasAuthentication, )

    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


class CasPersonalAccessToken(JSONAPIBaseView, generics.CreateAPIView):

    view_category = 'cas'
    view_name = 'cas-personal-access-token'

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


class CasOAuthScopes(JSONAPIBaseView, generics.CreateAPIView):

    view_category = 'cas'
    view_name = 'cas-oauth-scopes'

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


class CasDeveloperApplications(JSONAPIBaseView, generics.CreateAPIView):

    view_category = 'cas'
    view_name = 'cas-developer-applications'

    serializer_class = JSONAPISerializer
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        service_type = data.get('serviceType')
        if not service_type or service_type != 'OAUTH_APPLICATIONS':
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


class CasInstitutions(JSONAPIBaseView, generics.CreateAPIView):
    view_category = 'cas'
    view_name = 'cas-institutions'

    serializer_class = JSONAPISerializer
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        service_type = data.get('serviceType')
        if not service_type or service_type != 'INSTITUTIONS':
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
                # delegation protocol not supported yet
                # 'delegationProtocol': institution.delegation_protocol,
            }
            content.update({key: value})

        return Response(content)
