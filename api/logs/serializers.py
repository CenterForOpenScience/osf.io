from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, Link

class LogSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['action'])

    id = ser.CharField(read_only=True, source='_id')

    date = ser.DateTimeField(read_only=True)
    action = ser.CharField()
    params = ser.DictField()

    nodes_logged = ser.SerializerMethodField()
    user = ser.SerializerMethodField()

    def get_user(self, log):
        return log.user._id

    def get_nodes_logged(self, log):
        return [n._id for n in log.node__logged]

    links = ser.SerializerMethodField()

    def get_links(self, log):
        links = {
            'nodes': {
                'related': [
                    Link('nodes:node-detail', kwargs={'node_id': n._id})
                    for n in log.node__logged
                ]
            }
        }
        links['user'] = {
            'related': Link('users:user-detail', kwargs={'user_id': log.user._id}),
        }
        return LinksField(links).to_representation(log)

    class Meta:
        type_ = 'logs'
