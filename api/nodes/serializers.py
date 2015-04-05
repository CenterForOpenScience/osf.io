from rest_framework import serializers as ser
from website.models import Node

class NodeSerializer(ser.Serializer):

    _id = ser.CharField(read_only=True)
    title = ser.CharField(required=True)
    description = ser.CharField(required=False)

    def create(self, validated_data):
        node = Node(**validated_data)
        node.save()
        return node
