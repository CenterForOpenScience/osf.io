from rest_framework import serializers as ser

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

    scopes = ser.ListField(help_text='Governs permissions associated with this token',
                           required=True,
                           child=ser.CharField())

    token_id = ser.CharField(read_only=True, allow_blank=True)

    date_last_used = ser.DateTimeField(help_text='The date this token was last used (automatically filled in)',
                                     read_only=True)

    class Meta:
        type_ = 'tokens'

    links = LinksField({
        'html': 'absolute_url'
    })

    def absolute_url(self, obj):
        return obj.absolute_url

    def to_representation(self, obj, envelope='data'):
        data = super(ApiOAuth2PersonalTokenSerializer, self).to_representation(obj, envelope)
        # Make sure users only see token_id on create
        if not self.context['request'].method == 'POST':
            try:
                if data.get('data').get('attributes').get('token_id'):
                    data['data']['attributes'].pop('token_id')
            except AttributeError:
                pass

        return data

    def create(self, validated_data):
        instance = ApiOAuth2PersonalToken(**validated_data)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        assert isinstance(instance, ApiOAuth2PersonalToken), 'instance must be an ApiOAuth2PersonalToken'
        for attr, value in validated_data.iteritems():
            if attr == 'token_id':
                continue
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance
