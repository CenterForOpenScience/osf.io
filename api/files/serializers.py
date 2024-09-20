from datetime import datetime
from collections import OrderedDict

from django.urls import resolve, reverse
from django.core.exceptions import ValidationError

from furl import furl
import pytz

from framework.auth.core import Auth

from osf.models import (
    BaseFileNode,
    DraftNode,
    OSFUser,
    Comment,
    Preprint,
    AbstractNode,
    Registration,
    Guid,
    Node,
)

from rest_framework import serializers as ser
from rest_framework.fields import SkipField
from website import settings
from website.util import api_v2_url

from addons.base.utils import get_mfr_url

from api.base.serializers import (
    FileRelationshipField,
    format_relationship_links,
    IDField,
    GuidOrIDField,
    JSONAPIListField,
    JSONAPISerializer,
    Link,
    LinksField,
    NodeFileHyperLinkField,
    RelationshipField,
    TypeField,
    WaterbutlerLink,
    VersionedDateTimeField,
    TargetField,
    HideIfPreprint,
    ShowIfVersion,
)
from api.base.utils import absolute_reverse, get_user_auth
from api.base.exceptions import Conflict
from api.base.versioning import get_kebab_snake_case_field

class CheckoutField(ser.HyperlinkedRelatedField):

    default_error_messages = {'invalid_data': 'Checkout must be either the current user or null'}
    json_api_link = True  # serializes to a links object

    def __init__(self, **kwargs):
        kwargs['queryset'] = True
        kwargs['read_only'] = False
        kwargs['required'] = False
        kwargs['allow_null'] = True
        kwargs['lookup_field'] = '_id'
        kwargs['lookup_url_kwarg'] = 'user_id'

        self.meta = {'id': 'user_id'}
        self.link_type = 'related'
        self.always_embed = kwargs.pop('always_embed', False)

        super().__init__('users:user-detail', **kwargs)

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
                    'version': request.parser_context['kwargs']['version'],
                },
            ),
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
                self.display_value(item),
            )
            for item in queryset
        ])

    def get_queryset(self):
        return OSFUser.objects.filter(guids___id=self.context['request'].user._id, guids___id__isnull=False)

    def get_url(self, obj, view_name, request, format):
        if obj is None:
            return {}
        lookup_value = getattr(obj, self.lookup_field)
        return absolute_reverse(
            self.view_name, kwargs={
                self.lookup_url_kwarg: lookup_value,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

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

        url = super().to_representation(value)

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


class FileNodeRelationshipField(RelationshipField):
    def to_representation(self, value):
        if not isinstance(value.target, AbstractNode):
            raise SkipField
        return super().to_representation(value)


def disambiguate_files_related_view(node):
    if isinstance(node, Preprint):
        return 'preprints:preprint-files'
    if node.type == 'osf.draftnode':
        return 'draft_nodes:node-files'
    if node.type == 'osf.node':
        return 'nodes:node-files'
    if node.type == 'osf.registration':
        return 'registrations:registration-files'


def disambiguate_files_related_view_kwargs(filenode):
    if isinstance(filenode.target, Preprint):
        return {'preprint_id': '<target._id>'}
    else:
        return {
            'node_id': '<target._id>',
            'path': '<path>',
            'provider': '<provider>',
        }

class BaseFileSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'name',
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
    guid = ser.SerializerMethodField(
        read_only=True,
        method_name='get_file_guid',
        help_text='OSF GUID for this file (if one has been assigned)',
    )
    checkout = CheckoutField()
    name = ser.CharField(read_only=True, help_text='Display name used in the general user interface')
    kind = ser.CharField(read_only=True, help_text='Either folder or file')
    path = ser.CharField(read_only=True, help_text='The unique path used to reference this object')
    size = ser.SerializerMethodField(read_only=True, help_text='The size of this file at this version')
    provider = ser.CharField(read_only=True, help_text='The Add-on service this file originates from')
    materialized_path = ser.CharField(
        read_only=True, help_text='The Unix-style path of this object relative to the provider root',
    )
    last_touched = VersionedDateTimeField(read_only=True, help_text='The last time this file had information fetched about it via the OSF')
    date_modified = VersionedDateTimeField(
        read_only=True,
        help_text='Timestamp when the file was last modified',
        required=False,
        allow_null=True,
    )
    date_created = ser.SerializerMethodField(read_only=True, help_text='Timestamp when the file was created')
    extra = ser.SerializerMethodField(read_only=True, help_text='Additional metadata about this file')
    tags = JSONAPIListField(child=FileTagField(), required=False)
    current_user_can_comment = ser.SerializerMethodField(help_text='Whether the current user is allowed to post comments')
    current_version = ser.IntegerField(help_text='Latest file version', read_only=True, source='current_version_number')
    delete_allowed = ser.BooleanField(read_only=True, required=False)

    parent_folder = RelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': '<parent._id>'},
        help_text='The folder in which this file exists',
    )
    files = NodeFileHyperLinkField(
        related_view=lambda node: disambiguate_files_related_view(node),
        view_lambda_argument='target',
        related_view_kwargs=lambda filenode: disambiguate_files_related_view_kwargs(filenode),
        kind='folder',
    )
    versions = NodeFileHyperLinkField(
        related_view='files:file-versions',
        related_view_kwargs={'file_id': '<_id>'},
        kind='file',
    )
    comments = HideIfPreprint(
        FileRelationshipField(
            related_view='nodes:node-comments',
            related_view_kwargs={'node_id': '<target._id>'},
            related_meta={'unread': 'get_unread_comments_count'},
            filter={'target': 'get_file_guid'},
        ),
    )

    links = LinksField({
        'info': Link('files:file-detail', kwargs={'file_id': '<_id>'}),
        'move': WaterbutlerLink(),
        'upload': WaterbutlerLink(),
        'delete': WaterbutlerLink(),
        'download': 'get_download_link',
        'render': 'get_render_link',
        'html': 'absolute_url',
        'new_folder': WaterbutlerLink(must_be_folder=True, kind='folder'),
    })

    def absolute_url(self, obj):
        if obj.is_file:
            # NOTE: furl encoding to be verified later
            url = furl(
                settings.DOMAIN,
                path=(obj.target._id, 'files', obj.provider, obj.path.lstrip('/')),
            )
            if obj.provider == 'dataverse':
                url.add(query_params={'version': obj.history[-1]['extra']['datasetVersion']})
            return url.url

    def get_download_link(self, obj):
        if obj.is_file:
            return get_file_download_link(obj, view_only=self.context['request'].query_params.get('view_only'))

    def get_render_link(self, obj):
        if obj.is_file:
            mfr_url = get_mfr_url(obj.target, obj.provider)
            download_url = self.get_download_link(obj)
            return get_file_render_link(mfr_url, download_url)

    class Meta:
        type_ = 'files'

    def get_size(self, obj):
        if obj.versions.exists():
            self.size = obj.versions.first().size
            return self.size
        return None

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

        if obj.provider == 'dataverse':
            extras.update(obj.history[-1]['extra'])

        return extras

    def get_current_user_can_comment(self, obj):
        user = self.context['request'].user
        auth = Auth(user if not user.is_anonymous else None)
        if isinstance(obj.target, AbstractNode):
            return obj.target.can_comment(auth)
        return False

    def get_unread_comments_count(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return 0
        return Comment.find_n_unread(user=user, node=obj.target, page='files', root_id=obj.get_guid()._id)

    def user_id(self, obj):
        # NOTE: obj is the user here, the meta field for
        # Hyperlinks is weird
        if obj:
            return obj._id
        return None

    def update(self, file, validated_data):
        assert isinstance(file, BaseFileNode), 'Instance must be a BaseFileNode'
        if 'tags' in validated_data:
            if file.provider != 'osfstorage':
                raise Conflict(f'File service provider {file.provider} does not support tags on the OSF.')
            auth = get_user_auth(self.context['request'])
            file.update_tags(set(validated_data.pop('tags', [])), auth=auth)

        if 'checkout' in validated_data:
            if isinstance(file.target, Registration):
                raise ValidationError('Registration files are static and cannot be checked in or out.')
            user = self.context['request'].user
            file.check_in_or_out(user, validated_data.pop('checkout'))

        # `validated_data` ignores Read-only fields in payload
        for attr, value in validated_data.items():
            setattr(file, attr, value)
        file.save()
        return file

    def is_valid(self, **kwargs):
        return super().is_valid(clean_html=False, **kwargs)

    def get_file_guid(self, obj):
        if obj:
            guid = obj.get_guid()
            if guid:
                return guid._id
        return None

    def get_absolute_url(self, obj):
        return api_v2_url(f'files/{obj._id}/')


class FileSerializer(BaseFileSerializer):
    node = ShowIfVersion(
        FileNodeRelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<target._id>'},
            help_text='The project that this file belongs to',
        ),
        min_version='2.0', max_version='2.7',
    )
    target = TargetField(link_type='related', meta={'type': 'get_target_type'})

    # Assigned via annotation. See api/files/annotations for info
    show_as_unviewed = ser.BooleanField(
        read_only=True,
        required=False,
        default=False,
        help_text='Whether to mark the file as unviewed for the current user',
    )

    cedar_metadata_records = RelationshipField(
        related_view='files:file-cedar-metadata-records-list',
        related_view_kwargs={'file_id': '<_id>'},
    )

    def get_target_type(self, obj):
        if isinstance(obj, Preprint):
            return 'preprints'
        elif isinstance(obj, DraftNode):
            return 'draft_nodes'
        elif isinstance(obj, Registration):
            return 'registrations'
        elif isinstance(obj, Node):
            return 'nodes'
        else:
            raise NotImplementedError()


class OsfStorageFileSerializer(FileSerializer):
    """ Overrides `filterable_fields` to make `last_touched` non-filterable
    """
    filterable_fields = frozenset([
        'id',
        'name',
        'kind',
        'path',
        'size',
        'provider',
        'tags',
    ])


class FileDetailSerializer(FileSerializer):
    """
    - Overrides FileSerializer to make id required
    - Files should return the id type they are queried with, but only in osfstorage is the id is reliably equivalent to
     the path attribute, so that should not be overridden.

    """
    id = GuidOrIDField(source='_id', required=True)

    def to_representation(self, value):
        data = super().to_representation(value)
        view = self.context['view']
        data['data']['links']['self'] = absolute_reverse(f'{view.view_category}:{view.view_name}', kwargs=view.kwargs)
        guid = Guid.load(view.kwargs['file_id'])
        if guid:
            data['data']['id'] = guid._id
        return data


class QuickFilesSerializer(BaseFileSerializer):
    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<target.creator._id>'},
        help_text='The user who uploaded this file',
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
    name = ser.SerializerMethodField()
    links = LinksField({
        'self': 'self_url',
        'html': 'absolute_url',
        'download': 'get_download_link',
        'render': 'get_render_link',
    })

    def get_name(self, obj):
        file = self.context['file']
        return obj.get_basefilenode_version(file).version_name

    class Meta:
        @staticmethod
        def get_type(request):
            return get_kebab_snake_case_field(request.version, 'file-versions')

    def self_url(self, obj):
        return absolute_reverse(
            'files:version-detail', kwargs={
                'version_id': obj.identifier,
                'file_id': self.context['view'].kwargs['file_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def absolute_url(self, obj):
        fobj = self.context['file']
        # NOTE: furl encoding to be verified later
        return furl(
            settings.DOMAIN,
            path=(fobj.target._id, 'files', fobj.provider, fobj.path.lstrip('/')),
            query={fobj.version_identifier: obj.identifier},  # TODO this can probably just be changed to revision or version
        ).url

    def get_absolute_url(self, obj):
        return self.self_url(obj)

    def get_download_link(self, obj):
        return get_file_download_link(
            self.context['file'], version=obj.identifier,
            view_only=self.context['request'].query_params.get('view_only'),
        )

    def get_render_link(self, obj):
        file = self.context['file']
        mfr_url = get_mfr_url(file.target, file.provider)
        download_url = self.get_download_link(obj)

        return get_file_render_link(mfr_url, download_url, version=obj.identifier)


def get_file_download_link(obj, version=None, view_only=None):
    guid = obj.get_guid()
    # Add '' to the path to ensure thare's a trailing slash
    # The trailing slash avoids a 301
    # NOTE: furl encoding to be verified later
    url = furl(
        settings.DOMAIN,
        path=('download', guid._id if guid else obj._id, ''),
    )

    if version:
        url.args[obj.version_identifier] = version

    if view_only:
        url.args['view_only'] = view_only
    return url.url


def get_file_render_link(mfr_url, download_url, version=None):
    download_url_args = {}
    if version:
        download_url_args['revision'] = version

    download_url_args['direct'] = None
    download_url_args['mode'] = 'render'

    # NOTE: furl encoding to be verified later
    render_url = furl(
        mfr_url,
        path=['render'],
        args={
            'url': furl(
                download_url,
                args=download_url_args,
            ),
        },
    )
    return render_url.url
