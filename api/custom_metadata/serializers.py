from rest_framework.fields import empty
import rest_framework.serializers as ser

from framework.auth.core import Auth
from api.base.serializers import (
    IDField,
    JSONAPISerializer,
    LinksField,
    RelationshipField,
)
from api.base.utils import absolute_reverse


REASONABLE_MAX_LENGTH = (2**16) - 1  # 65535


class AlwaysRequiredCharField(ser.CharField):
    def __init__(self, *args, **kwargs):
        if not kwargs.get("required", True):
            raise ValueError(
                "AlwaysRequiredCharField does not accept required=False",
            )
        super().__init__(*args, **kwargs, required=True)

    def validate_empty_values(self, data):
        # override Field.validate_empty_values:
        #   this field is required even in a PATCH request
        #   (where the root serializer has partial=True)
        if data is empty:
            self.fail("required")
        return super().validate_empty_values(data)


class FundingInfoSerializer(ser.Serializer):
    funder_name = AlwaysRequiredCharField(
        allow_blank=False,
        max_length=REASONABLE_MAX_LENGTH,
    )
    funder_identifier = ser.CharField(
        allow_blank=True,
        default="",
        max_length=REASONABLE_MAX_LENGTH,
    )
    funder_identifier_type = ser.ChoiceField(
        choices=["ISNI", "GRID", "Crossref Funder ID", "ROR", "Other"],
        allow_blank=True,
        default="",
    )
    award_number = ser.CharField(
        allow_blank=True,
        default="",
        max_length=REASONABLE_MAX_LENGTH,
    )
    award_uri = ser.URLField(
        allow_blank=True,
        default="",
        max_length=REASONABLE_MAX_LENGTH,
    )
    award_title = ser.CharField(
        allow_blank=True,
        default="",
        max_length=REASONABLE_MAX_LENGTH,
    )


class CustomItemMetadataSerializer(JSONAPISerializer):
    non_anonymized_fields = {
        "id",
        "guid",
        "resource_type_general",
        "language",
    }

    id = IDField(read_only=True, source="guid._id")
    guid = RelationshipField(
        read_only=True,
        related_view="guids:guid-detail",
        related_view_kwargs={"guids": "<guid._id>"},
    )
    language = ser.CharField(
        required=False,
        allow_blank=True,
        max_length=REASONABLE_MAX_LENGTH,
    )
    resource_type_general = ser.CharField(
        required=False,
        allow_blank=True,
        max_length=REASONABLE_MAX_LENGTH,
    )
    funders = FundingInfoSerializer(
        many=True,
        source="funding_info",
        required=False,
    )
    links = LinksField(
        {
            "self": "get_absolute_url",
        },
    )

    class Meta:
        type_ = "custom-item-metadata-records"

    def update(self, guid_metadata_record, validated_data):
        user = self.context["request"].user
        guid_metadata_record.update(validated_data, Auth(user))
        return guid_metadata_record

    def get_absolute_url(self, obj):
        return absolute_reverse(
            "custom-item-metadata:custom-item-metadata-detail",
            kwargs={
                "guid_id": obj.guid._id,
                "version": self.context["request"].parser_context["kwargs"][
                    "version"
                ],
            },
        )


class CustomFileMetadataSerializer(CustomItemMetadataSerializer):
    non_anonymized_fields = (
        CustomItemMetadataSerializer.non_anonymized_fields
        | {
            "title",
            "description",
        }
    )

    title = ser.CharField(required=False, allow_blank=True)  # TODO: max-length
    description = ser.CharField(
        required=False,
        allow_blank=True,
    )  # TODO: max-length

    class Meta:
        type_ = "custom-file-metadata-records"

    def get_absolute_url(self, obj):
        return absolute_reverse(
            "custom-file-metadata:custom-file-metadata-detail",
            kwargs={
                "guid_id": obj.guid._id,
                "version": self.context["request"].parser_context["kwargs"][
                    "version"
                ],
            },
        )
