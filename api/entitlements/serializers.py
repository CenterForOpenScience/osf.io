from rest_framework import serializers as ser


class LoginAvailabilitySerializer(ser.Serializer):
    institution_id = ser.IntegerField(required=True, read_only=True)
    entitlements = ser.ListField(required=True, child=ser.CharField())
