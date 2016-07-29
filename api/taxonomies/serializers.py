from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer

class TaxonomySerializer(JSONAPISerializer):
    type = ser.CharField(max_length = 200)
    text = ser.CharField(max_length = 200)
    parent_id = ser.CharField(max_length = 200)

    class Meta:
        type_ = 'taxonomies'