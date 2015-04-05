from rest_framework import generics, permissions

from .serializers import NodeSerializer

class NodeList(generics.ListCreateAPIView):
    """Return a list of nodes. By default, a GET
    will return a list of nodes the current user contributes
    to.
    """
    permission_classes = (
        permissions.IsAuthenticated,
    )
    serializer_class = NodeSerializer

    # override
    def get_queryset(self):
        user = self.request.user
        # Return list of nodes that current user contributes to
        return user.node__contributed

    # override
    def perform_create(self, serializer):
        # On creation, make sure that current user is the creator
        user = self.request.user
        serializer.save(creator=user)
