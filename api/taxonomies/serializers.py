from rest_framework import serializers as ser

class TaxonomySerializer(ser.Serializer):
    data = ser.JSONField()
