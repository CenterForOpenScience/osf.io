from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from api.base.throttling import TestUserRateThrottle, TestAnonRateThrottle


@api_view(['GET'])
@throttle_classes([TestUserRateThrottle, TestAnonRateThrottle])
def test_throttling(request):
    return Response('Throttle test.')
