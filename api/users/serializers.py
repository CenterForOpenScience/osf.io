from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, Link


class UserSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    fullname = ser.CharField()
    given_name = ser.CharField()
    middle_name = ser.CharField(source='middle_names')
    family_name = ser.CharField()
    suffix = ser.CharField()
    date_registered = ser.DateTimeField(read_only=True)
    gravatar_url = ser.CharField()
    employment_institutions = ser.ListField(source='jobs')
    educational_institutions = ser.ListField(source='schools')
    social_accounts = ser.DictField(source='social')

    links = LinksField({
        'html': 'absolute_url',
        'nodes': {
            'relation': Link('users:user-nodes', kwargs={'pk': '<pk>'})
        }
    })

    class Meta:
        type_ = 'users'

    def absolute_url(self, obj):
        return obj.absolute_url

    def update(self, instance, validated_data):
        # TODO
        pass
