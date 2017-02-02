from django.contrib.auth.models import AnonymousUser

from rest_framework import generics
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.base.permissions import TokenHasScope
from api.base.serializers import JSONAPISerializer
from api.base.views import JSONAPIBaseView
from api.cas.auth import CasAuthentication

from framework.auth.oauth_scopes import CoreScopes


class CasLogin(JSONAPIBaseView, generics.CreateAPIView):

    permission_classes = (
        IsAuthenticated,
        TokenHasScope,
    )

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

    permission_classes = (
        IsAuthenticated,
        TokenHasScope,
    )

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

    permission_classes = (
        IsAuthenticated,
        TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'cas'
    view_name = 'cas-institution-authenticate'

    serializer_class = JSONAPISerializer

    authentication_classes = (CasAuthentication,)

    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)
