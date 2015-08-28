import furl

from rest_framework import serializers as ser

from website import settings
from api.base.utils import absolute_reverse
from api.base.serializers import JSONAPISerializer, LinksField, Link


class FileSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'name',
        'node',
        'path',
        'provider',
        'last_touched',
    ])
    id = ser.CharField(read_only=True, source='_id')
    name = ser.CharField(help_text='Display name used in the general user interface')
    path = ser.CharField(help_text='The unique path used to reference this object')
    provider = ser.CharField(help_text='The Add-on service this file originates from')
    last_touched = ser.DateTimeField(help_text='The last time this file had information fetched about it via the OSF')
    # history = ser.ListField(ser.DictField(), help_text='A raw dump of the metadata recieved whenever infomation is fetched about it')

    links = LinksField({
        'html': 'absolute_url',
        'self': Link('files:file-detail', kwargs={'file_id': '<_id>'}),
        'node': {'relation': Link('nodes:node-detail', kwargs={'node_id': '<node._id>'})},
        'versions': {'relation': Link('files:file-versions', kwargs={'file_id': '<_id>'})},
    })

    class Meta:
        type_ = 'files'

    def absolute_url(self, obj):
        return furl.furl(settings.DOMAIN).set(
            path=(obj.node._id, 'files', obj.provider, obj.path.lstrip('/'))
        ).url

    def update(self, instance, validated_data):
        # TODO
        pass


class FileVersionSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'size',
        'identifier',
        'content_type',
    ])
    id = ser.CharField(read_only=True, source='_id')
    size = ser.IntegerField(help_text='The size of this file at this version')
    identifier = ser.CharField(help_text='This version\'s unique identifier from it\'s original service')
    content_type = ser.CharField(help_text='The mime type of this file at this verison')
    links = LinksField({
        'self': 'self_url',
        'html': 'absolute_url'
    })

    class Meta:
        type_ = 'file_version'

    def self_url(self, obj):
        return absolute_reverse('files:version-detail', kwargs={
            'version_id': obj._id,
            'file_id': self.context['view'].kwargs['file_id']
        })

    def absolute_url(self, obj):
        fobj = self.context['view'].get_file()
        return furl.furl(settings.DOMAIN).set(
            path=(fobj.node._id, 'files', fobj.provider, fobj.path.lstrip('/')),
            query={fobj.version_idenifier: obj.identifier}
        ).url

    def update(self, instance, validated_data):
        pass
