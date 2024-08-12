from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField
from api.base.utils import absolute_reverse


class CedarMetadataTemplateSerializer(JSONAPISerializer):
    class Meta:
        type_ = "cedar-metadata-templates"

    filterable_fields = frozenset(["schema_name", "cedar_id", "active"])

    id = ser.CharField(source="_id", read_only=True)
    schema_name = ser.CharField(read_only=True)
    cedar_id = ser.CharField(read_only=True)
    template = ser.DictField(read_only=True)
    active = ser.BooleanField(read_only=True)
    template_version = ser.IntegerField(read_only=True)

    links = LinksField({"self": "get_absolute_url"})

    def get_absolute_url(self, obj):
        return absolute_reverse(
            "cedar-metadata-templates:cedar-metadata-template-detail",
            kwargs={"template_id": obj._id},
        )
