import logging

from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.base.permissions import TokenHasScope
from api.entitlements.serializers import (
    LoginAvailabilitySerializer,
)
from osf.models import InstitutionEntitlement, Institution

logger = logging.getLogger(__name__)


class LoginAvailability(APIView):
    view_category = 'institutions'
    view_name = 'login_availability'
    parser_classes = (JSONParser,)
    permission_classes = (TokenHasScope,)

    def get_serializer_class(self):
        return None

    def _get_embed_partial(self):
        return None

    def post(self, request, *args, **kwargs):
        serializer = LoginAvailabilitySerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            institution_guid = data.get('institution_id')
            institution = Institution.load(institution_guid)
            if institution is None:
                return Response({'login_availability': False}, status=status.HTTP_200_OK)
            entitlements = data.get('entitlements')
            entitlement_list = InstitutionEntitlement.objects.filter(
                institution_id=institution,
                entitlement__in=entitlements,
            )
            login_availability = all(list(entitlement_list.values_list('login_availability', flat=True)))
            return Response({'login_availability': login_availability}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
