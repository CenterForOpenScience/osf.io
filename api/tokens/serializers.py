from rest_framework import serializers as ser
from rest_framework import exceptions

from framework.auth.oauth_scopes import public_scopes
from website.models import ApiOAuth2PersonalToken

from api.base.serializers import JSONAPISerializer, LinksField, IDField, TypeField


class ApiOAuth2PersonalTokenSerializer(JSONAPISerializer):
    """Serialize data about a registered personal access token"""

    id = IDField(source='_id', read_only=True, help_text='The object ID for this token (automatically generated)')
    type = TypeField()

    name = ser.CharField(help_text='A short, descriptive name for this token',
                         required=True)

    owner = ser.CharField(help_text='The user who owns this token',
                          read_only=True,  # Don't let user register a token in someone else's name
                          source='owner._id')

    scopes = ser.CharField(help_text='Governs permissions associated with this token',
                           required=True)

    token_id = ser.CharField(read_only=True, allow_blank=True)

    class Meta:
        type_ = 'tokens'

    links = LinksField({
        'html': 'absolute_url'
    })

    def absolute_url(self, obj):
        return obj.absolute_url

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def to_representation(self, obj, envelope='data'):
        data = super(ApiOAuth2PersonalTokenSerializer, self).to_representation(obj, envelope=envelope)
        # Make sure users only see token_id on create
        if not self.context['request'].method == 'POST':
            if 'data' in data:
                data['data']['attributes'].pop('token_id')
            else:
                data['attributes'].pop('token_id')

        return data

    def create(self, validated_data):
        validate_requested_scopes(validated_data)
        instance = ApiOAuth2PersonalToken(**validated_data)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        validate_requested_scopes(validated_data)
        assert isinstance(instance, ApiOAuth2PersonalToken), 'instance must be an ApiOAuth2PersonalToken'

        instance.deactivate(save=False)  # This will cause CAS to revoke the existing token but still allow it to be used in the future, new scopes will be updated properly at that time.
        instance.reload()

        for attr, value in validated_data.iteritems():
            if attr == 'token_id':  # Do not allow user to update token_id
                continue
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance

def validate_requested_scopes(validated_data):
    scopes_set = set(validated_data['scopes'].split(' '))
    for scope in scopes_set:
        if scope not in public_scopes or not public_scopes[scope].is_public:
            raise exceptions.ValidationError('User requested invalid scope')
