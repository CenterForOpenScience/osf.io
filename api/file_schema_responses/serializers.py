from framework.auth import Auth
from rest_framework import serializers as ser

from api.base.serializers import (
    IDField,
    JSONAPISerializer,
    LinksField,
    RelationshipField,
    TypeField,
)
from api.base.utils import absolute_reverse
from api.base.versioning import get_kebab_snake_case_field


class FileSchemaResponseSerializer(JSONAPISerializer):
    writeable_method_fields = [
        'responses',
    ]

    id = IDField(source='_id', required=True)
    type = TypeField()

    responses = ser.SerializerMethodField()

    schema_blocks = RelationshipField(
        related_view='schemas:registration-schema-blocks',
        related_view_kwargs={'schema_id': '<_id>'},
    )
    parent = RelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': '<file._id>'},
    )

    schema = RelationshipField(
        related_view='schemas:file-metadata-schema-detail',
        related_view_kwargs={'schema_id': '<schema._id>'},
    )

    links = LinksField({
        'download': 'get_download_link',
        'self': 'get_absolute_url',
    })

    def get_responses(self, obj):
        return obj.responses

    def update(self, schema_response, validated_data):
        file = schema_response.parent
        target = file.target
        user = self.context['request'].user
        responses = validated_data.pop('responses')
        schema_response.set_responses(responses)
        schema_response.save()

        target.add_log(
            action=target.log_class.FILE_METADATA_UPDATED,
            params={
                'path': file.materialized_path,
            },
            auth=Auth(user),
        )

        return schema_response

    def get_download_link(self, obj):
        return absolute_reverse(
            'files:file_schema_responses:file-schema-response-download', kwargs={
                'file_id': obj.parent._id,
                'file_schema_response_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    class Meta:
        @staticmethod
        def get_type(request):
            return get_kebab_snake_case_field(request.version, 'file-schema-response')
