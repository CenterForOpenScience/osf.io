from rest_framework import serializers as ser

from website.models import NodeLog

from api.base.serializers import JSONAPISerializer, LinksField, Link

class LogSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['action'])

    id = ser.CharField(read_only=True, source='_id')

    date = ser.DateTimeField(read_only=True)
    action = ser.CharField(help_text='One of: {0}'.format(', '.join(NodeLog.actions())))
    params = ser.DictField()

    nodes_logged = ser.SerializerMethodField(help_text='A list of node primary keys for nodes associated with this log')
    user = ser.SerializerMethodField(help_text='The user associated with this log')

    def get_user(self, log):
        return log._render_log_contributor(log.user._id)

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
