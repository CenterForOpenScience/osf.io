from datetime import datetime
from collections import OrderedDict

from django.core.urlresolvers import resolve, reverse
import furl
import pytz

from framework.auth.core import Auth
from osf.models import BaseFileNode, OSFUser, Comment
from rest_framework import serializers as ser
from website import settings
from website.util import api_v2_url

from api.base.serializers import (
    FileCommentRelationshipField,
    format_relationship_links,
    IDField,
    JSONAPIListField,
    JSONAPISerializer,
    Link,
    LinksField,
    NodeFileHyperLinkField,
    RelationshipField,
    TypeField,
    WaterbutlerLink,
    VersionedDateTimeField,
)
from api.base.exceptions import Conflict
from api.base.utils import absolute_reverse
from api.base.utils import get_user_auth

class CheckoutField(ser.HyperlinkedRelatedField):

    default_error_messages = {'invalid_data': 'Checkout must be either the current user or null'}
    json_api_link = True  # serializes to a links object

    def __init__(self, **kwargs):
        kwargs['queryset'] = True
        kwargs['read_only'] = False
        kwargs['allow_null'] = True
        kwargs['lookup_field'] = '_id'
        kwargs['lookup_url_kwarg'] = 'user_id'

        self.meta = {'id': 'user_id'}
        self.link_type = 'related'
        self.always_embed = kwargs.pop('always_embed', False)

        super(CheckoutField, self).__init__('users:user-detail', **kwargs)

    def resolve(self, resource, field_name, request):
        """
        Resolves the view when embedding.
        """
        embed_value = resource.checkout._id
        return resolve(
            reverse(
                self.view_name,
                kwargs={
                    self.lookup_url_kwarg: embed_value,
                    'version': request.parser_context['kwargs']['version']
                }
            )
        )

    def get_choices(self, cutoff=None):
        """Most of this was copied and pasted from rest_framework's RelatedField -- we needed to pass the
        correct value of a user's pk as a choice, while avoiding our custom implementation of `to_representation`
        which returns a dict for JSON API purposes.
        """
        queryset = self.get_queryset()
        if queryset is None:
            # Ensure that field.choices returns something sensible
            # even when accessed with a read-only field.
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return OrderedDict([
            (
                item.pk,
                self.display_value(item)
            )
            for item in queryset
        ])

    def get_queryset(self):
        return OSFUser.objects.filter(guids___id=self.context['request'].user._id)

    def get_url(self, obj, view_name, request, format):
        if obj is None:
            return {}
        lookup_value = getattr(obj, self.lookup_field)
        return absolute_reverse(self.view_name, kwargs={
            self.lookup_url_kwarg: lookup_value,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

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
        if value and hasattr(value, '_id'):
            rel_meta = {'id': value._id}

        ret = format_relationship_links(related_link=url, rel_meta=rel_meta)
        return ret


class FileTagField(ser.Field):
    def to_representation(self, obj):
        if obj is not None:
            return obj.name
        return None

    def to_internal_value(self, data):
        return data


class BaseFileSerializer(JSONAPISerializer):
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
    guid = ser.SerializerMethodField(read_only=True,
                                     method_name='get_file_guid',
                                     help_text='OSF GUID for this file (if one has been assigned)')
    checkout = CheckoutField()
    name = ser.CharField(read_only=True, help_text='Display name used in the general user interface')
    kind = ser.CharField(read_only=True, help_text='Either folder or file')
    path = ser.CharField(read_only=True, help_text='The unique path used to reference this object')
    size = ser.SerializerMethodField(read_only=True, help_text='The size of this file at this version')
    provider = ser.CharField(read_only=True, help_text='The Add-on service this file originates from')
    materialized_path = ser.CharField(
        read_only=True, help_text='The Unix-style path of this object relative to the provider root')
    last_touched = VersionedDateTimeField(read_only=True, help_text='The last time this file had information fetched about it via the OSF')
    date_modified = ser.SerializerMethodField(read_only=True, help_text='Timestamp when the file was last modified')
    date_created = ser.SerializerMethodField(read_only=True, help_text='Timestamp when the file was created')
    extra = ser.SerializerMethodField(read_only=True, help_text='Additional metadata about this file')
    tags = JSONAPIListField(child=FileTagField(), required=False)
    current_user_can_comment = ser.SerializerMethodField(help_text='Whether the current user is allowed to post comments')
    current_version = ser.IntegerField(help_text='Latest file version', read_only=True, source='current_version_number')
    delete_allowed = ser.BooleanField(read_only=True, required=False)

    files = NodeFileHyperLinkField(
        related_view='nodes:node-files',
        related_view_kwargs={'node_id': '<node._id>', 'path': '<path>', 'provider': '<provider>'},
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
                                            filter={'target': 'get_file_guid'}
                                            )

    links = LinksField({
        'info': Link('files:file-detail', kwargs={'file_id': '<_id>'}),
        'move': WaterbutlerLink(),
        'upload': WaterbutlerLink(),
        'delete': WaterbutlerLink(),
        'download': 'get_download_link',
        'new_folder': WaterbutlerLink(must_be_folder=True, kind='folder'),
    })

    def get_download_link(self, obj):
        if obj.is_file:
            return get_file_download_link(obj, view_only=self.context['request'].query_params.get('view_only'))

    class Meta:
        type_ = 'files'

    def get_size(self, obj):
        if obj.versions.exists():
            self.size = obj.versions.first().size
            return self.size
        return None

    def get_date_modified(self, obj):
        mod_dt = None
        if obj.provider == 'osfstorage' and obj.versions.exists():
            # Each time an osfstorage file is added or uploaded, a new version object is created with its
            # date_created equal to the time of the update.  The external_modified is the modified date
            # from the backend the file is stored on.  This field refers to the modified date on osfstorage,
            # so prefer to use the created of the latest version.
            mod_dt = obj.versions.first().created
        elif obj.provider != 'osfstorage' and obj.history:
            mod_dt = obj.history[-1].get('modified', None)

        if self.context['request'].version >= '2.2' and obj.is_file and mod_dt:
            return datetime.strftime(mod_dt, '%Y-%m-%dT%H:%M:%S.%fZ')

        return mod_dt and mod_dt.replace(tzinfo=pytz.utc)

    def get_date_created(self, obj):
        creat_dt = None
        if obj.provider == 'osfstorage' and obj.versions.exists():
            creat_dt = obj.versions.last().created
        elif obj.provider != 'osfstorage' and obj.history:
            # Non-osfstorage files don't store a created date, so instead get the modified date of the
            # earliest entry in the file history.
            creat_dt = obj.history[0].get('modified', None)

        if self.context['request'].version >= '2.2' and obj.is_file and creat_dt:
            return datetime.strftime(creat_dt, '%Y-%m-%dT%H:%M:%S.%fZ')

        return creat_dt and creat_dt.replace(tzinfo=pytz.utc)

    def get_extra(self, obj):
        metadata = {}
        if obj.provider == 'osfstorage' and obj.versions.exists():
            metadata = obj.versions.first().metadata
        elif obj.provider != 'osfstorage' and obj.history:
            metadata = obj.history[-1].get('extra', {})

        extras = {}
        extras['hashes'] = {  # mimic waterbutler response
            'md5': metadata.get('md5', None),
            'sha256': metadata.get('sha256', None),
        }
        if obj.provider == 'osfstorage' and obj.is_file:
            extras['downloads'] = obj.get_download_count()
        return extras

    def get_current_user_can_comment(self, obj):
        user = self.context['request'].user
        auth = Auth(user if not user.is_anonymous else None)
        return obj.node.can_comment(auth)

    def get_unread_comments_count(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return 0
        return Comment.find_n_unread(user=user, node=obj.node, page='files', root_id=obj.get_guid()._id)

    def user_id(self, obj):
        # NOTE: obj is the user here, the meta field for
        # Hyperlinks is weird
        if obj:
            return obj._id
        return None

    def update(self, instance, validated_data):
        assert isinstance(instance, BaseFileNode), 'Instance must be a BaseFileNode'
        if instance.provider != 'osfstorage' and 'tags' in validated_data:
            raise Conflict('File service provider {} does not support tags on the OSF.'.format(instance.provider))
        auth = get_user_auth(self.context['request'])
        old_tags = set(instance.tags.values_list('name', flat=True))
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
        return super(BaseFileSerializer, self).is_valid(clean_html=False, **kwargs)

    def get_file_guid(self, obj):
        if obj:
            guid = obj.get_guid()
            if guid:
                return guid._id
        return None

    def get_absolute_url(self, obj):
        return api_v2_url('files/{}/'.format(obj._id))


class FileSerializer(BaseFileSerializer):
    node = RelationshipField(related_view='nodes:node-detail',
                             related_view_kwargs={'node_id': '<node._id>'},
                             help_text='The project that this file belongs to'
                             )


class OsfStorageFileSerializer(FileSerializer):
    """ Overrides `filterable_fields` to make `last_touched` non-filterable
    """
    filterable_fields = frozenset([
        'id',
        'name',
        'node',
        'kind',
        'path',
        'size',
        'provider',
        'tags',
    ])

    def create(self, validated_data):
        return super(OsfStorageFileSerializer, self).create(validated_data)


class FileDetailSerializer(FileSerializer):
    """
    Overrides FileSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class QuickFilesSerializer(BaseFileSerializer):
    user = RelationshipField(related_view='users:user-detail',
                             related_view_kwargs={'user_id': '<node.creator._id>'},
                             help_text='The user who uploaded this file'
                             )


class QuickFilesDetailSerializer(QuickFilesSerializer):
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
    date_created = VersionedDateTimeField(source='created', read_only=True, help_text='The date that this version was created')
    links = LinksField({
        'self': 'self_url',
        'html': 'absolute_url',
        'download': 'get_download_link',
    })

    class Meta:
        type_ = 'file_versions'

    def self_url(self, obj):
        return absolute_reverse('files:version-detail', kwargs={
            'version_id': obj.identifier,
            'file_id': self.context['view'].kwargs['file_id'],
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def absolute_url(self, obj):
        fobj = self.context['file']
        return furl.furl(settings.DOMAIN).set(
            path=(fobj.node._id, 'files', fobj.provider, fobj.path.lstrip('/')),
            query={fobj.version_identifier: obj.identifier}  # TODO this can probably just be changed to revision or version
        ).url

    def get_absolute_url(self, obj):
        return self.self_url(obj)

    def get_download_link(self, obj):
        return get_file_download_link(
            self.context['file'], version=obj.identifier,
            view_only=self.context['request'].query_params.get('view_only')
        )


def get_file_download_link(obj, version=None, view_only=None):
    guid = obj.get_guid()
    # Add '' to the path to ensure thare's a trailing slash
    # The trailing slash avoids a 301
    url = furl.furl(settings.DOMAIN).set(
        path=('download', guid._id if guid else obj._id, ''),
    )

    if version:
        url.args[obj.version_identifier] = version

    if view_only:
        url.args['view_only'] = view_only
    return url.url
