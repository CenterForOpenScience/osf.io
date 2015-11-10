import furl
from modularodm import Q

from rest_framework import serializers as ser

from website import settings
from framework.auth.core import User
from website.files.models import FileNode
from api.base.utils import absolute_reverse
from api.base.serializers import NodeFileHyperLink, WaterbutlerLink
from api.base.serializers import JSONAPIHyperlinkedIdentityField
from api.base.serializers import Link, JSONAPISerializer, LinksField, IDField, TypeField

class CheckoutField(JSONAPIHyperlinkedIdentityField):

    default_error_messages = {'invalid_data': 'Checkout must be either the current user or null'}

    def __init__(self, **kwargs):
        kwargs['queryset'] = True
        kwargs['read_only'] = False
        kwargs['allow_null'] = True
        kwargs['lookup_field'] = 'pk'
        kwargs['lookup_url_kwarg'] = 'user_id'

        self.meta = {'id': 'user_id'}
        self.link_type = 'related'

        super(ser.HyperlinkedIdentityField, self).__init__('users:user-detail', **kwargs)

    def get_queryset(self):
        return User.find(Q('_id', 'eq', self.context['request'].user._id))

    def get_url(self, obj, view_name, request, format):
        if obj is None:
            return None
        return super(ser.HyperlinkedIdentityField, self).get_url(obj, view_name, request, format)

    def to_internal_value(self, data):
        if data is None:
            return None
        try:
            return next(
                user for user in
                self.get_queryset()
                if user._id == data
            )
        except StopIteration:
            self.fail('invalid_data')


class FileSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'name',
        'node',
        'kind',
        'path',
        'size',
        'provider',
        'last_touched',
    ])
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    checkout = CheckoutField()
    name = ser.CharField(read_only=True, help_text='Display name used in the general user interface')
    kind = ser.CharField(read_only=True, help_text='Either folder or file')
    path = ser.CharField(read_only=True, help_text='The unique path used to reference this object')
    size = ser.SerializerMethodField(read_only=True, help_text='The size of this file at this version')
    provider = ser.CharField(read_only=True, help_text='The Add-on service this file originates from')
    last_touched = ser.DateTimeField(read_only=True, help_text='The last time this file had information fetched about it via the OSF')
    date_modified = ser.SerializerMethodField(read_only=True, help_text='The size of this file at this version')

    files = NodeFileHyperLink(kind='folder', link_type='related', view_name='nodes:node-files', kwargs=('node_id', 'path', 'provider'))
    versions = NodeFileHyperLink(kind='file', link_type='related', view_name='files:file-versions', kwargs=(('file_id', '_id'), ))

    links = LinksField({
        'info': Link('files:file-detail', kwargs={'file_id': '<_id>'}),
        'move': WaterbutlerLink(),
        'upload': WaterbutlerLink(),
        'delete': WaterbutlerLink(),
        'download': WaterbutlerLink(must_be_file=True),
        'new_folder': WaterbutlerLink(must_be_folder=True, kind='folder')
    })

    class Meta:
        type_ = 'files'

    def get_size(self, obj):
        if obj.versions:
            return obj.versions[-1].size
        return None

    def get_date_modified(self, obj):
        if obj.versions:
            if obj.provider == 'osfstorage':
                # Odd case osfstorage's date created is when the version was create
                # (when the file was modified) its date modified is referencing whatever backend it is on
                return obj.versions[-1].date_created
            return obj.versions[-1].date_modified
        return None

    def user_id(self, obj):
        # NOTE: obj is the user here, the meta field for
        # Hyperlinks is weird
        if obj:
            return obj._id
        return None

    def update(self, instance, validated_data):
        assert isinstance(instance, FileNode), 'Instance must be a FileNode'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def is_valid(self, **kwargs):
        return super(FileSerializer, self).is_valid(clean_html=False, **kwargs)


class FileDetailSerializer(FileSerializer):
    """
    Overrides FileSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class FileVersionSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'size',
        'identifier',
        'content_type',
    ])
    id = ser.CharField(read_only=True, source='identifier')
    size = ser.IntegerField(read_only=True, help_text='The size of this file at this version')
    content_type = ser.CharField(read_only=True, help_text='The mime type of this file at this verison')
    links = LinksField({
        'self': 'self_url',
        'html': 'absolute_url'
    })

    class Meta:
        type_ = 'file_versions'

    def self_url(self, obj):
        return absolute_reverse('files:version-detail', kwargs={
            'version_id': obj.identifier,
            'file_id': self.context['view'].kwargs['file_id']
        })

    def absolute_url(self, obj):
        fobj = self.context['view'].get_file()
        return furl.furl(settings.DOMAIN).set(
            path=(fobj.node._id, 'files', fobj.provider, fobj.path.lstrip('/')),
            query={fobj.version_identifier: obj.identifier}  # TODO this can probably just be changed to revision or version
        ).url
