from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer
from website.project.model import DraftRegistration
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
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


