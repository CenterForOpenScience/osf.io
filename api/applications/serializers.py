from django.core.validators import URLValidator
from rest_framework import serializers as ser

from modularodm import Q

from website.models import ApiOAuth2Application

from api.base.serializers import JSONAPISerializer, LinksField, IDField, TypeField
from api.base.utils import absolute_reverse


class ApiOAuthApplicationBaseSerializer(JSONAPISerializer):
    """Base serializer class for OAuth2 applications """
    id = IDField(source='client_id', read_only=True, help_text='The client ID for this application (automatically generated)')

    type = TypeField()

    client_id = ser.CharField(help_text='The client ID for this application (automatically generated)',
                              read_only=True)

    client_secret = ser.CharField(help_text='The client secret for this application (automatically generated)',
                                  read_only=True)  # TODO: May change this later

    links = LinksField({
        'html': 'absolute_url',
        'reset': 'reset_url'
    })

    def absolute_url(self, obj):
        return obj.absolute_url

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    def reset_url(self, obj):
        return absolute_reverse('applications:application-reset', kwargs={'client_id': obj.client_id})

    class Meta:
        type_ = 'applications'


class ApiOAuth2ApplicationSerializer(ApiOAuthApplicationBaseSerializer):
    """Serialize data about a registered OAuth2 application"""

    id = IDField(source='client_id', read_only=True, help_text='The client ID for this application (automatically generated)')

    type = TypeField()

    name = ser.CharField(help_text='A short, descriptive name for this application',
                         required=True)

    description = ser.CharField(help_text='An optional description displayed to all users of this application',
                                required=False,
                                allow_blank=True)
    home_url = ser.CharField(help_text="The full URL to this application's homepage.",
                             required=True,
                             validators=[URLValidator()],
                             label='Home URL')

    callback_url = ser.CharField(help_text='The callback URL for this application (refer to OAuth documentation)',
                                 required=True,
                                 validators=[URLValidator()],
                                 label='Callback URL')

    owner = ser.CharField(help_text='The id of the user who owns this application',
                          read_only=True,  # Don't let user register an application in someone else's name
                          source='owner._id')

    date_created = ser.DateTimeField(help_text='The date this application was generated (automatically filled in)',
                                     read_only=True)

    def create(self, validated_data):
        instance = ApiOAuth2Application(**validated_data)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        assert isinstance(instance, ApiOAuth2Application), 'instance must be an ApiOAuth2Application'
        for attr, value in validated_data.iteritems():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ApiOAuth2ApplicationDetailSerializer(ApiOAuth2ApplicationSerializer):
    """
    Overrides ApiOAuth2ApplicationSerializer to make id required.
    """

    id = IDField(source='client_id', required=True, help_text='The client ID for this application (automatically generated)')


class ApiOAuth2ApplicationResetSerializer(ApiOAuth2ApplicationDetailSerializer):

    def absolute_url(self, obj):
        obj = ApiOAuth2Application.find_one(Q('client_id', 'eq', obj['client_id']))
        return obj.absolute_url

    def reset_url(self, obj):
        return absolute_reverse('applications:application-reset', kwargs={'client_id': obj['client_id']})
