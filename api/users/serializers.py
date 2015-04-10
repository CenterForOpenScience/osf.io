from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, Link

class UserSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    fullname = ser.CharField()
    date_registered = ser.DateTimeField(read_only=True)

    links = LinksField({
        'html': 'absolute_url',
        'children': {
            'related': Link('nodes:node-children', pk='<pk>')
        },
        'contributors': {
            'related': Link('nodes:node-contributors', pk='<pk>')
        },
        'registrations': {
            'related': Link('nodes:node-registrations', pk='<pk>')
        },
    })
    # TODO: finish me

    class Meta:
        type_ = 'users'

    def update(self, instance, validated_data):
        # TODO
        pass
