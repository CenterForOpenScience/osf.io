import datetime

from rest_framework import serializers as ser

from website.project.views import drafts
from api.base.serializers import JSONAPISerializer
from website.project.model import DraftRegistration
from website.project.model import Q
from website.project.metadata.schemas import OSF_META_SCHEMAS

from rest_framework import serializers as ser


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
        updated = datetime.datetime.utcnow()
        schema_version = int(validated_data.get('schema_version', 1))
        instance.initiated = instance.initiated
        if "registration_form" in validated_data.keys() and "schema_version" in validated_data.keys():
            schema_name = validated_data['registration_form']
            meta_schema = drafts.get_schema_or_fail(
                Q('name', 'eq', schema_name) &
                Q('schema_version', 'eq', schema_version)
            )
            instance.registration_schema = meta_schema
            instance.updated = updated
        else:
            instance.registration_schema = instance.registration_schema

        if "registration_metadata" in validated_data.keys():
            instance.registration_metadata = validated_data.get('registration_metadata', {})
            instance.updated = updated

        instance.save()
        return instance
