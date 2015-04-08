from rest_framework.decorators import api_view
from rest_framework.response import Response

from .utils import absolute_reverse

@api_view(('GET',))
def root(request, format=None):

    if request.user and not request.user.is_anonymous():
        user = request.user
        # TODO: Use user serializer
        current_user = {
            'id': user.pk,
            'fullname': user.fullname,
        }
    else:
        current_user = None
    return Response({
        'message': 'Welcome to the OSF API v2',
        'current_user': current_user,
        'links': {
            'nodes': absolute_reverse('nodes:node-list'),
            'users': absolute_reverse('users:user-list'),
        }
    })
