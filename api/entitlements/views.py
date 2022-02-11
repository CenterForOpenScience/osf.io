from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.entitlements.serializers import (
    LoginAvailabilitySerializer,
)
from osf.models import InstitutionEntitlement


class LoginAvailability(APIView):
    view_category = 'institutions'
    view_name = 'login_availability'

    def post(self, request, format=None):
        serializer = LoginAvailabilitySerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            institution_id = data.get('institution_id')
            entitlements = data.get('entitlements')
            entitlement_list = InstitutionEntitlement.objects.filter(institution_id=institution_id, entitlement__in=entitlements)
            login_availability = all(list(entitlement_list.values_list('login_availability', flat=True)))
            return Response({"login_availability": login_availability}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
