from rest_framework import serializers as ser
from api.base.utils import absolute_reverse

from api.base.serializers import JSONAPISerializer

class UserSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    fullname = ser.CharField()
    date_registered = ser.DateTimeField(read_only=True)
    # TODO: finish me

    class Meta:
        type_ = 'users'

    def get_links(self, obj):
        return {
            'html': obj.absolute_url,
            'nodes': {
                'relation': absolute_reverse('users:user-nodes', kwargs={'pk': obj.pk})
            }
        }

    def update(self, instance, validated_data):
        # TODO
        pass
