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

from osf.models import ApiOAuth2PersonalToken, OSFUser


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

    def post(self, request, *args, **kwargs):

        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        token_id = data.get('token_id')
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
            'userId': user._id,
            'scopes': token.scopes,
        }

        return Response(content)


class CasOAuthScopes(JSONAPIBaseView, generics.CreateAPIView):
    view_category = 'cas'
    view_name = 'cas-oauth-scopes'

    def post(self, request, *args, **kwargs):
        raise AuthenticationFailed(detail=util.API_NOT_IMPLEMENTED)


class CasOAuthApplications(JSONAPIBaseView, generics.CreateAPIView):
    view_category = 'cas'
    view_name = 'cas-oauth-applications'

    def post(self, request, *args, **kwargs):
        raise AuthenticationFailed(detail=util.API_NOT_IMPLEMENTED)


class CasInstitutions(JSONAPIBaseView, generics.CreateAPIView):
    view_category = 'cas'
    view_name = 'cas-institutions'

    def post(self, request, *args, **kwargs):
        raise AuthenticationFailed(detail=util.API_NOT_IMPLEMENTED)
