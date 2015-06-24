from rest_framework import serializers as ser

from api.nodes.serializers import NodeSerializer


class RegistrationSerializer(NodeSerializer):
    is_registration_draft = ser.BooleanField(read_only=True)
