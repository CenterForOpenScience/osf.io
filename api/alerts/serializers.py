from django.apps import apps
from rest_framework import serializers as ser
from django.core.exceptions import ValidationError

from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
    TypeField,
    IDField,
)
from api.base.exceptions import InvalidModelValueError


class AlertSerializer(JSONAPISerializer):
    filterable_fields = frozenset(['location', 'id'])

    id = IDField(source='_id')
    type = TypeField()
    location = ser.CharField(max_length=255)

    links = LinksField({'self': 'get_absolute_url'})

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    class Meta:
        type_ = 'alerts'

    def create(self, validated_data):
        Alert = apps.get_model('osf.DismissedAlert')
        alert = Alert(**validated_data)
        try:
            alert.save()
        except ValidationError as e:
            raise InvalidModelValueError(detail=e.messages[0])

        return alert
