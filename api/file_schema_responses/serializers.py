from framework.auth import Auth
from rest_framework import serializers as ser

from api.base.serializers import (
    IDField,
    JSONAPISerializer,
    LinksField,
    RelationshipField,
    TypeField,
)
from api.base.versioning import get_kebab_snake_case_field
from osf.models import (
    FileSchemaBlock,
    FileSchemaResponseBlock,
)
from rest_framework.exceptions import ValidationError


class FileSchemaResponseSerializer(JSONAPISerializer):
    writeable_method_fields = [
        'responses',
    ]

    id = IDField(source='_id', required=True)
    type = TypeField()

    responses = ser.SerializerMethodField()

    schema_blocks = RelationshipField(
        related_view='schemas:file-schema-block-list',
        related_view_kwargs={'schema_id': '<_id>'},
    )
    parent = RelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': '<file._id>'},
    )

    schema = RelationshipField(
        related_view='schemas:file-schema-detail',
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
        schema_response.schema.validate_metadata(responses)

        question_blocks = FileSchemaBlock.objects.filter(
            schema=schema_response.schema,
            response_key__in=list(responses.keys()),
        )

        for source_block in question_blocks:
            block, created = FileSchemaResponseBlock.objects.get_or_create(
                source_schema_response=schema_response,
                source_schema_block=source_block,
                schema_key=source_block.response_key,
            )
            schema_response.response_blocks.add(block)
            block.set_response(responses.pop(source_block.response_key))

        if responses:
            raise ValidationError(f'Your response contained invalid keys: {",".join(list(responses.keys()))}')

        schema_response.save()

        target.add_log(
            action=target.log_class.FILE_SCHEMA_RESPONSE_UPDATED,
            params={
                'path': file.materialized_path,
            },
            auth=Auth(user),
        )

        return schema_response

    def get_download_link(self, obj):
        return 'link to SHARE'

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    class Meta:
        @staticmethod
        def get_type(request):
            return get_kebab_snake_case_field(request.version, 'file-schema-response')
