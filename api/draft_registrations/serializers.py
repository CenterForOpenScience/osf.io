import datetime

from rest_framework import serializers as ser

from website.project.views import drafts
from api.base.serializers import JSONAPISerializer
from website.project.model import DraftRegistration
from website.project.model import Q
from website.project.metadata.schemas import OSF_META_SCHEMAS



class DraftRegSerializer(JSONAPISerializer):
    schema_choices = [schema['name'] for schema in OSF_META_SCHEMAS]
    id = ser.CharField(read_only=True, source='_id')
    branched_from = ser.CharField(read_only = True, help_text="Source node")
    initiator = ser.CharField(read_only=True)
    registration_schema = ser.CharField(read_only=True)
    registration_form = ser.ChoiceField(choices=schema_choices, required=True, write_only=True, help_text="Please select a registration form to initiate registration.")
    registration_metadata = ser.CharField(required=False, help_text="Responses to supplemental registration questions")
    schema_version = ser.IntegerField(help_text="Registration schema version", write_only=True)
    initiated = ser.DateTimeField(read_only=True)
    updated = ser.DateTimeField(read_only=True)
    completion = ser.CharField(read_only=True)

    class Meta:
        type_='draft-registrations'


    def update(self, instance, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        assert isinstance(instance, DraftRegistration), 'instance must be a DraftRegistration'
        schema_name = validated_data['registration_form']
        schema_version = int(validated_data.get('schema_version', 1))
        if schema_name:
            meta_schema = drafts.get_schema_or_fail(
                Q('name', 'eq', schema_name) &
                Q('schema_version', 'eq', schema_version)
            )
            existing_schema = instance.registration_schema
            if existing_schema is None or (existing_schema.name, existing_schema.schema_version) != (meta_schema.name, meta_schema.schema_version):
                instance.registration_schema = meta_schema
        if not instance.registration_metadata:
            instance.registration_metadata = validated_data.get('registration_metadata', {})
        instance.updated = datetime.datetime.utcnow()
        instance.save()
        return instance
