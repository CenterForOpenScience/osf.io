from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer

class UserSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    fullname = ser.CharField()
    # TODO: finish me

    class Meta:
        type_ = 'users'

    def get_links(self, obj):
        return {
            'html': obj.absolute_url,
        }

    def update(self, instance, validated_data):
        # TODO
        pass
