from django.core.validators import URLValidator
from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError

from website.models import ApiOAuth2Application

from api.base.exceptions import Conflict
from api.base.serializers import JSONAPISerializer, LinksField


class ApiOAuth2ApplicationSerializer(JSONAPISerializer):
    """Serialize data about a registered OAuth2 application"""
    id = ser.CharField(help_text='The client ID for this application (automatically generated)',
                       read_only=True,
                       source='client_id',
                       label='ID')
    type = ser.CharField(write_only=True, required=True)

    client_id = ser.CharField(help_text='The client ID for this application (automatically generated)',
                              read_only=True)

    client_secret = ser.CharField(help_text='The client secret for this application (automatically generated)',
                                  read_only=True)  # TODO: May change this later

    owner = ser.CharField(help_text='The id of the user who owns this application',
                          read_only=True,  # Don't let user register an application in someone else's name
                          source='owner._id')

    name = ser.CharField(help_text='A short, descriptive name for this application',
                         required=True)

    description = ser.CharField(help_text='An optional description displayed to all users of this application',
                                required=False,
                                allow_blank=True)

    date_created = ser.DateTimeField(help_text='The date this application was generated (automatically filled in)',
                                     read_only=True)

    home_url = ser.CharField(help_text="The full URL to this application's homepage.",
                             required=True,
                             validators=[URLValidator()],
                             label="Home URL")

    callback_url = ser.CharField(help_text='The callback URL for this application (refer to OAuth documentation)',
                                 required=True,
                                 validators=[URLValidator()],
                                 label="Callback URL")

    class Meta:
        type_ = 'applications'

    def validate_type(self, value):
        if self.Meta.type_ != value:
            raise Conflict()
        return value

    links = LinksField({
        'html': 'absolute_url'
    })

    def absolute_url(self, obj):
        return obj.absolute_url

    def create(self, validated_data):
        instance = ApiOAuth2Application(**validated_data)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        validated_id = validated_data.get('id', None)
        if not validated_id:
            validated_id = validated_data.get('_id', None)
        validated_type = validated_data.get('type', None)

        errors = {}
        if not validated_id:
            errors['id'] = ['This field is required.']
        if not validated_type:
            errors['type'] = ['This field is required.']

        if errors:
            raise ValidationError(errors)

        assert isinstance(instance, ApiOAuth2Application), 'instance must be an ApiOAuth2Application'
        for attr, value in validated_data.iteritems():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ApiOAuth2ApplicationUpdateSerializer(ApiOAuth2ApplicationSerializer):
    id = ser.CharField(source='_id', label='ID', required=True)

    def validate_id(self, value):
        if self._args[0]._id != value:
            raise Conflict()
        return value
