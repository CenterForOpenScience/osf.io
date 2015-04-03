from rest_framework import serializers

class NodeSerializer(serializers.Serializer):

    _id = serializers.CharField()
    title = serializers.CharField()
