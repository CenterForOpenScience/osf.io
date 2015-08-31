from rest_framework import serializers as ser

from website.models import NodeLog

from api.base.serializers import JSONAPISerializer, LinksField, Link

class LogUserSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='user._id')
    fullname = ser.CharField(read_only=True, source='user.fullname')

class NestedField(ser.Field):

    filterable_fields = frozenset(['id', 'fullname'])

    def __init__(self, attrs, *args, **kwargs):
        super(NestedField, self).__init__(*args, **kwargs)
        self.attrs = attrs

    def to_representation(self, obj):
        ret = {}
        for field, serializer in self.attrs.iteritems():
            ret[field] = serializer.to_representation(obj)
        return ret

class LogSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['action'])

    id = ser.CharField(read_only=True, source='_id')

    date = ser.DateTimeField(read_only=True)
    action = ser.CharField(help_text='One of: {0}'.format(', '.join(NodeLog.actions())))
    params = ser.DictField()

    links = LinksField({
        'nodes': {
            'related': Link('logs:log-nodes', kwargs={'log_id': '<_id>'})
        },
        'user': {
            'related': Link('users:user-detail', kwargs={'user_id': '<user._id>'})
        }
    })

    class Meta:
        type_ = 'logs'
