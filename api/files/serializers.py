import furl
import pytz
from modularodm import Q

from rest_framework import serializers as ser
from django.core.urlresolvers import resolve, reverse

from website import settings
from framework.auth.core import User
from website.files.models import FileNode
from website.project.model import Comment
from api.base.utils import absolute_reverse
from api.base.serializers import (
    NodeFileHyperLinkField,
    WaterbutlerLink,
    format_relationship_links,
    FileCommentRelationshipField,
    JSONAPIListField,
    Link,
    JSONAPISerializer,
    LinksField,
    IDField,
    TypeField,
)
from api.base.exceptions import Conflict
from api.base.utils import get_user_auth
from website.util import api_v2_url


class CheckoutField(ser.HyperlinkedRelatedField):

    default_error_messages = {'invalid_data': 'Checkout must be either the current user or null'}
    json_api_link = True  # serializes to a links object

    def __init__(self, **kwargs):
        kwargs['queryset'] = True
        kwargs['read_only'] = False
        kwargs['allow_null'] = True
        kwargs['lookup_field'] = 'pk'
        kwargs['lookup_url_kwarg'] = 'user_id'

        self.meta = {'id': 'user_id'}
        self.link_type = 'related'
        self.always_embed = kwargs.pop('always_embed', False)

        super(CheckoutField, self).__init__('users:user-detail', **kwargs)

    def resolve(self, resource):
        """
        Resolves the view when embedding.
        """
        embed_value = resource.stored_object.checkout.pk
        kwargs = {self.lookup_url_kwarg: embed_value}
        return resolve(
            reverse(
                self.view_name,
                kwargs=kwargs
            )
        )

    def get_queryset(self):
        return User.find(Q('_id', 'eq', self.context['request'].user._id))

    def get_url(self, obj, view_name, request, format):
        if obj is None:
            return {}
        return super(CheckoutField, self).get_url(obj, view_name, request, format)

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

    def to_representation(self, value):

        url = super(CheckoutField, self).to_representation(value)

        rel_meta = None
        if value:
            rel_meta = {'id': value._id}

        ret = format_relationship_links(related_link=url, rel_meta=rel_meta)
        return ret


class FileTagField(ser.Field):
    def to_representation(self, obj):
        if obj is not None:
            return obj._id
        return None

    def to_internal_value(self, data):
        return data


class FileSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'name',
        'node',
        'kind',
        'path',
        'materialized_path',
        'size',
        'provider',
        'last_touched',
        'tags',
    ])
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    checkout = CheckoutField()
    name = ser.CharField(read_only=True, help_text='Display name used in the general user interface')
    kind = ser.CharField(read_only=True, help_text='Either folder or file')
    path = ser.CharField(read_only=True, help_text='The unique path used to reference this object')
    size = ser.SerializerMethodField(read_only=True, help_text='The size of this file at this version')
    provider = ser.CharField(read_only=True, help_text='The Add-on service this file originates from')
    materialized_path = ser.CharField(
        read_only=True, help_text='The Unix-style path of this object relative to the provider root')
    last_touched = ser.DateTimeField(read_only=True, help_text='The last time this file had information fetched about it via the OSF')
    date_modified = ser.SerializerMethodField(read_only=True, help_text='Timestamp when the file was last modified')
    date_created = ser.SerializerMethodField(read_only=True, help_text='Timestamp when the file was created')
    extra = ser.SerializerMethodField(read_only=True, help_text='Additional metadata about this file')
    tags = JSONAPIListField(child=FileTagField(), required=False)
    file_guid = ser.SerializerMethodField(read_only=True, help_text='The unique id of this file')

    files = NodeFileHyperLinkField(
        related_view='nodes:node-files',
        related_view_kwargs={'node_id': '<node_id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder'
    )
    versions = NodeFileHyperLinkField(
        related_view='files:file-versions',
        related_view_kwargs={'file_id': '<_id>'},
        kind='file'
    )
    comments = FileCommentRelationshipField(related_view='nodes:node-comments',
                                            related_view_kwargs={'node_id': '<node._id>'},
                                            related_meta={'unread': 'get_unread_comments_count'},
                                            filter={'target': 'get_file_guid'})
    links = LinksField({
        'info': Link('files:file-detail', kwargs={'file_id': '<_id>'}),
        'move': WaterbutlerLink(),
        'upload': WaterbutlerLink(),
        'delete': WaterbutlerLink(),
        'download': WaterbutlerLink(must_be_file=True),
        'new_folder': WaterbutlerLink(must_be_folder=True, kind='folder'),
    })

    class Meta:
        type_ = 'files'

    def get_size(self, obj):
        if obj.versions:
            return obj.versions[-1].size
        return None

    def get_date_modified(self, obj):
        mod_dt = None
        if obj.provider == 'osfstorage' and obj.versions:
            # Each time an osfstorage file is added or uploaded, a new version object is created with its
            # date_created equal to the time of the update.  The date_modified is the modified date
            # from the backend the file is stored on.  This field refers to the modified date on osfstorage,
            # so prefer to use the date_created of the latest version.
            mod_dt = obj.versions[-1].date_created
        elif obj.provider != 'osfstorage' and obj.history:
            mod_dt = obj.history[-1].get('modified', None)

        return mod_dt and mod_dt.replace(tzinfo=pytz.utc)

    def get_date_created(self, obj):
        creat_dt = None
        if obj.provider == 'osfstorage' and obj.versions:
            creat_dt = obj.versions[0].date_created
        elif obj.provider != 'osfstorage' and obj.history:
            # Non-osfstorage files don't store a created date, so instead get the modified date of the
            # earliest entry in the file history.
            creat_dt = obj.history[0].get('modified', None)

        return creat_dt and creat_dt.replace(tzinfo=pytz.utc)

    def get_extra(self, obj):
        metadata = {}
        if obj.provider == 'osfstorage' and obj.versions:
            metadata = obj.versions[-1].metadata
        elif obj.provider != 'osfstorage' and obj.history:
            metadata = obj.history[-1].get('extra', {})

        extras = {}
        extras['hashes'] = {  # mimic waterbutler response
            'md5': metadata.get('md5', None),
            'sha256': metadata.get('sha256', None),
        }
        return extras

    def get_unread_comments_count(self, obj):
        user = self.context['request'].user
        if user.is_anonymous():
            return 0
        return Comment.find_n_unread(user=user, node=obj.node, page='files', root_id=obj.get_guid()._id)

    def user_id(self, obj):
        # NOTE: obj is the user here, the meta field for
        # Hyperlinks is weird
        if obj:
            return obj._id
        return None

    def update(self, instance, validated_data):
        assert isinstance(instance, FileNode), 'Instance must be a FileNode'
        if instance.provider != 'osfstorage' and 'tags' in validated_data:
            raise Conflict('File service provider {} does not support tags on the OSF.'.format(instance.provider))
        auth = get_user_auth(self.context['request'])
        old_tags = set([tag._id for tag in instance.tags])
        if 'tags' in validated_data:
            current_tags = set(validated_data.pop('tags', []))
        else:
            current_tags = set(old_tags)

        for new_tag in (current_tags - old_tags):
            instance.add_tag(new_tag, auth=auth)
        for deleted_tag in (old_tags - current_tags):
            instance.remove_tag(deleted_tag, auth=auth)

        for attr, value in validated_data.items():
            if attr == 'checkout':
                user = self.context['request'].user
                instance.check_in_or_out(user, value)
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance

    def is_valid(self, **kwargs):
        return super(FileSerializer, self).is_valid(clean_html=False, **kwargs)

    def get_file_guid(self, obj):
        if obj:
            return obj.get_guid(create=True)._id
        return None

    def get_absolute_url(self, obj):
        return api_v2_url('files/{}/'.format(obj._id))


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

    def get_absolute_url(self, obj):
        return self.self_url(obj)
