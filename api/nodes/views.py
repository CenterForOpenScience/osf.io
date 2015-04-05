from rest_framework import generics, permissions

from .serializers import NodeSerializer

class NodeList(generics.ListAPIView):
    """Return a list of nodes. By default, a GET
    will return a list of nodes the current user contributes
    to.
    """
    permission_classes = (
        permissions.IsAuthenticated,
    )
    serializer_class = NodeSerializer

    def get_queryset(self):
        user = self.request.user
        # Return list of nodes that current user contributes to
        return user.node__contributed
