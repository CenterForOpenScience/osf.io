from rest_framework import serializers as ser

from website.models import ApiOAuth2PersonalToken

from api.base.serializers import JSONAPISerializer, LinksField, IDField, TypeField


class ApiOAuth2PersonalTokenSerializer(JSONAPISerializer):
    """Serialize data about a registered personal access token"""

    id = IDField(source='token_id', read_only=True, help_text='The token for this application (automatically generated)')
    type = TypeField()
    name = ser.CharField(help_text='A short, descriptive name for this application',
                         required=True)
    user_id = ser.CharField(help_text='The id of the user who owns this application',
                          read_only=True,  # Don't let user register an application in someone else's name
                          source='owner._id')

    date_last_used = ser.DateTimeField(help_text='The date this application was generated (automatically filled in)',
                                     read_only=True)

    class Meta:
        type_ = 'tokens'

    links = LinksField({
    })

    def create(self, validated_data):
        instance = ApiOAuth2PersonalToken(**validated_data)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        assert isinstance(instance, ApiOAuth2PersonalToken), 'instance must be an ApiOAuth2PersonalToken'
        for attr, value in validated_data.iteritems():
            setattr(instance, attr, value)
        instance.save()
        return instance
