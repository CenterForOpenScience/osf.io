from website.models import Node
from rest_framework import generics, permissions
from rest_framework.response import Response

from .serializers import NodeSerializer

class NodeList(generics.ListAPIView):
    permission_classes = (
        permissions.IsAuthenticated,
    )
    serializer_class = NodeSerializer

    def get_queryset(self):
        return Node.find()
