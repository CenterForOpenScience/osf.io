from django.contrib.auth.models import AnonymousUser

from rest_framework import generics
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response

from api.base.views import JSONAPIBaseView
from api.base.serializers import JSONAPISerializer
from api.cas.auth import CasAuthentication


class CasLogin(JSONAPIBaseView, generics.CreateAPIView):

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
            #     "status": "AUTHENTICATION SUCCESS",
            #     "userId": "",
            #     "attributes": {
            #         "username": "",
            #         "givenName": "",
            #         "familyName": "",
            #     },
            # }
            content = {
                "status": "AUTHENTICATION SUCCESS",
                "userId": request.user._id,
                "attributes": {
                    "username": request.user.username,
                    "givenName": request.user.given_name,
                    "familyName": request.user.family_name,
                }
            }

        return Response(content)


class CasRegister(JSONAPIBaseView, generics.CreateAPIView):

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
            #     "status": "REGISTRATION_SUCCESS"
            # }
            content = {
                "status": "REGISTRATION_SUCCESS",
            }

        return Response(content)
