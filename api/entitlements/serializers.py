from rest_framework import serializers as ser


class LoginAvailabilitySerializer(ser.Serializer):
    institution_id = ser.CharField(required=True)
    entitlements = ser.ListField(required=True, child=ser.CharField())
