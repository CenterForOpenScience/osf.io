from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, Link


class UserSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    fullname = ser.CharField()
    date_registered = ser.DateTimeField(read_only=True)

    links = LinksField({
        'html': 'absolute_url',
        'nodes': {
            'relation': Link('users:user-nodes', kwargs={'pk': '<pk>'})
        }
    })
    # TODO: finish me

    class Meta:
        type_ = 'users'

    def update(self, instance, validated_data):
        # TODO
        pass
