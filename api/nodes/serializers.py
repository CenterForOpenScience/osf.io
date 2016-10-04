from rest_framework import serializers as ser
from rest_framework import exceptions

from modularodm import Q
from modularodm.exceptions import ValidationValueError

from framework.auth.core import Auth
from framework.exceptions import PermissionsError

from django.conf import settings

from website.addons.base.exceptions import InvalidFolderError, InvalidAuthError
from website.project.metadata.schemas import ACTIVE_META_SCHEMAS, LATEST_SCHEMA_VERSION
from website.project.metadata.utils import is_prereg_admin_not_project_admin
from website.models import Node, Comment, Institution, MetaSchema, DraftRegistration, PrivateLink
from website.exceptions import NodeStateError
from website.util import permissions as osf_permissions
from website.project import new_private_link
from website.project.model import NodeUpdateError

from api.base.utils import get_user_auth, get_object_or_error, absolute_reverse, is_truthy
from api.base.serializers import (JSONAPISerializer, WaterbutlerLink, NodeFileHyperLinkField, IDField, TypeField,
                                  TargetTypeField, JSONAPIListField, LinksField, RelationshipField,
                                  HideIfRegistration, RestrictedDictSerializer,
                                  JSONAPIRelationshipSerializer, relationship_diff, )
from api.base.exceptions import (InvalidModelValueError,
                                 RelationshipPostMakesNoChanges, Conflict,
                                 EndpointNotImplementedError)
from api.base.settings import ADDONS_FOLDER_CONFIGURABLE

from website.oauth.models import ExternalAccount


class NodeTagField(ser.Field):
    def to_representation(self, obj):
        if obj is not None:
            return obj._id
        return None

    def to_internal_value(self, data):
        return data


class NodeLicenseSerializer(RestrictedDictSerializer):

    copyright_holders = ser.ListField(allow_empty=True, read_only=True)
    year = ser.CharField(allow_blank=True, read_only=True)


class NodeCitationSerializer(JSONAPISerializer):
    id = IDField(read_only=True)
    title = ser.CharField(allow_blank=True, read_only=True)
    author = ser.ListField(read_only=True)
    publisher = ser.CharField(allow_blank=True, read_only=True)
    type = ser.CharField(allow_blank=True, read_only=True)
    doi = ser.CharField(allow_blank=True, read_only=True)

    links = LinksField({'self': 'get_absolute_url'})

    def get_absolute_url(self, obj):
        return obj['URL']

    class Meta:
        type_ = 'node-citation'

class NodeCitationStyleSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True)
    citation = ser.CharField(allow_blank=True, read_only=True)

    def get_absolute_url(self, obj):
        return obj['URL']

    class Meta:
        type_ = 'styled-citations'


class NodeSerializer(JSONAPISerializer):
    # TODO: If we have to redo this implementation in any of the other serializers, subclass ChoiceField and make it
    # handle blank choices properly. Currently DRF ChoiceFields ignore blank options, which is incorrect in this
    # instance
    filterable_fields = frozenset([
        'id',
        'title',
        'description',
        'public',
        'tags',
        'category',
        'date_created',
        'date_modified',
        'root',
        'parent',
        'contributors',
        'preprint'
    ])

    non_anonymized_fields = [
        'id',
        'title',
        'description',
        'category',
        'date_created',
        'date_modified',
        'registration',
        'tags',
        'public',
        'license',
        'links',
        'children',
        'comments',
        'contributors',
        'files',
        'node_links',
        'parent',
        'root',
        'logs',
        'wikis'
    ]

    id = IDField(source='_id', read_only=True)
    type = TypeField()

    category_choices = settings.NODE_CATEGORY_MAP.items()
    category_choices_string = ', '.join(["'{}'".format(choice[0]) for choice in category_choices])

    title = ser.CharField(required=True)
    description = ser.CharField(required=False, allow_blank=True, allow_null=True)
    category = ser.ChoiceField(choices=category_choices, help_text='Choices: ' + category_choices_string)
    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    registration = ser.BooleanField(read_only=True, source='is_registration')
    preprint = ser.BooleanField(read_only=True, source='is_preprint')
    fork = ser.BooleanField(read_only=True, source='is_fork')
    collection = ser.BooleanField(read_only=True, source='is_collection')
    tags = JSONAPIListField(child=NodeTagField(), required=False)
    node_license = NodeLicenseSerializer(read_only=True, required=False)
    template_from = ser.CharField(required=False, allow_blank=False, allow_null=False,
                                  help_text='Specify a node id for a node you would like to use as a template for the '
                                            'new node. Templating is like forking, except that you do not copy the '
                                            'files, only the project structure. Some information is changed on the top '
                                            'level project by submitting the appropriate fields in the request body, '
                                            'and some information will not change. By default, the description will '
                                            'be cleared and the project will be made private.')

    current_user_can_comment = ser.SerializerMethodField(help_text='Whether the current user is allowed to post comments')
    current_user_permissions = ser.SerializerMethodField(help_text='List of strings representing the permissions '
                                                                   'for the current user on this node.')

    # Public is only write-able by admins--see update method
    public = ser.BooleanField(source='is_public', required=False,
                              help_text='Nodes that are made public will give read-only access '
                                        'to everyone. Private nodes require explicit read '
                                        'permission. Write and admin access are the same for '
                                        'public and private nodes. Administrators on a parent '
                                        'node have implicit read permissions for all child nodes')

    links = LinksField({'html': 'get_absolute_html_url'})
    # TODO: When we have osf_permissions.ADMIN permissions, make this writable for admins

    license = RelationshipField(
        related_view='licenses:license-detail',
        related_view_kwargs={'license_id': '<node_license.node_license._id>'},
    )

    children = RelationshipField(
        related_view='nodes:node-children',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_node_count'},
    )

    comments = RelationshipField(
        related_view='nodes:node-comments',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'unread': 'get_unread_comments_count'},
        filter={'target': '<pk>'}
    )

    contributors = RelationshipField(
        related_view='nodes:node-contributors',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_contrib_count'},
    )

    files = RelationshipField(
        related_view='nodes:node-providers',
        related_view_kwargs={'node_id': '<pk>'}
    )

    wikis = RelationshipField(
        related_view='nodes:node-wikis',
        related_view_kwargs={'node_id': '<pk>'}
    )

    forked_from = RelationshipField(
        related_view=lambda n: 'registrations:registration-detail' if getattr(n, 'is_registration', False) else 'nodes:node-detail',
        related_view_kwargs={'node_id': '<forked_from_id>'}
    )

    template_node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<template_node._id>'}
    )

    forks = RelationshipField(
        related_view='nodes:node-forks',
        related_view_kwargs={'node_id': '<pk>'}
    )

    node_links = RelationshipField(
        related_view='nodes:node-pointers',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_pointers_count'},
    )

    parent = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<parent_node._id>'},
        filter_key='parent_node'
    )

    draft_registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-draft-registrations',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-registrations',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_registration_count'}
    ))

    affiliated_institutions = RelationshipField(
        related_view='nodes:node-institutions',
        related_view_kwargs={'node_id': '<pk>'},
        self_view='nodes:node-relationships-institutions',
        self_view_kwargs={'node_id': '<pk>'}
    )

    root = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<root._id>'}
    )

    logs = RelationshipField(
        related_view='nodes:node-logs',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_logs_count'}
    )

    linked_nodes = RelationshipField(
        related_view='nodes:linked-nodes',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_node_links_count'},
        self_view='nodes:node-pointer-relationship',
        self_view_kwargs={'node_id': '<pk>'},
        self_meta={'count': 'get_node_links_count'}
    )

    view_only_links = RelationshipField(
        related_view='nodes:node-view-only-links',
        related_view_kwargs={'node_id': '<pk>'},
    )

    citation = RelationshipField(
        related_view='nodes:node-citation',
        related_view_kwargs={'node_id': '<pk>'}
    )

    def get_current_user_permissions(self, obj):
        user = self.context['request'].user
        if user.is_anonymous():
            return ['read']
        permissions = obj.get_permissions(user=user)
        if not permissions:
            permissions = ['read']
        return permissions

    def get_current_user_can_comment(self, obj):
        user = self.context['request'].user
        auth = Auth(user if not user.is_anonymous() else None)
        return obj.can_comment(auth)

    class Meta:
        type_ = 'nodes'

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    # TODO: See if we can get the count filters into the filter rather than the serializer.

    def get_logs_count(self, obj):
        return len(obj.logs)

    def get_node_count(self, obj):
        auth = get_user_auth(self.context['request'])
        nodes = [node for node in obj.nodes if node.can_view(auth) and node.primary and not node.is_deleted]
        return len(nodes)

    def get_contrib_count(self, obj):
        return len(obj.contributors)

    def get_registration_count(self, obj):
        auth = get_user_auth(self.context['request'])
        registrations = [node for node in obj.registrations_all if node.can_view(auth)]
        return len(registrations)

    def get_pointers_count(self, obj):
        return len(obj.nodes_pointer)

    def get_node_links_count(self, obj):
        count = 0
        auth = get_user_auth(self.context['request'])
        for pointer in obj.nodes_pointer:
            if not pointer.node.is_deleted and not pointer.node.is_collection and pointer.node.can_view(auth):
                count += 1
        return count

    def get_unread_comments_count(self, obj):
        user = get_user_auth(self.context['request']).user
        node_comments = Comment.find_n_unread(user=user, node=obj, page='node')

        return {
            'node': node_comments
        }

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        if 'template_from' in validated_data:
            template_from = validated_data.pop('template_from')
            template_node = Node.load(key=template_from)
            if template_node is None:
                raise exceptions.NotFound
            if not template_node.has_permission(user, 'read', check_parent=False):
                raise exceptions.PermissionDenied

            validated_data.pop('creator')
            changed_data = {template_from: validated_data}
            node = template_node.use_as_template(auth=get_user_auth(request), changes=changed_data)
        else:
            node = Node(**validated_data)
        try:
            node.save()
        except ValidationValueError as e:
            raise InvalidModelValueError(detail=e.message)
        if is_truthy(request.GET.get('inherit_contributors')) and validated_data['parent'].has_permission(user, 'write'):
            auth = get_user_auth(request)
            parent = validated_data['parent']
            contributors = []
            for contributor in parent.contributors:
                if contributor is not user:
                    contributors.append({
                        'user': contributor,
                        'permissions': parent.get_permissions(contributor),
                        'visible': parent.get_visible(contributor)
                    })

                if not contributor.is_registered:
                    node.add_unregistered_contributor(
                        fullname=contributor.fullname, email=contributor.email, auth=auth,
                        permissions=parent.get_permissions(contributor), existing_user=contributor
                    )

                node.add_contributors(contributors, auth=auth, log=True, save=True)
        return node

    def update(self, node, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        assert isinstance(node, Node), 'node must be a Node'
        auth = get_user_auth(self.context['request'])
        old_tags = set([tag._id for tag in node.tags])
        if 'tags' in validated_data:
            current_tags = set(validated_data.pop('tags', []))
        elif self.partial:
            current_tags = set(old_tags)
        else:
            current_tags = set()

        for new_tag in (current_tags - old_tags):
            node.add_tag(new_tag, auth=auth)
        for deleted_tag in (old_tags - current_tags):
            node.remove_tag(deleted_tag, auth=auth)

        if validated_data:
            try:
                node.update(validated_data, auth=auth)
            except ValidationValueError as e:
                raise InvalidModelValueError(detail=e.message)
            except PermissionsError:
                raise exceptions.PermissionDenied
            except NodeUpdateError as e:
                raise exceptions.ValidationError(detail=e.reason)
            except NodeStateError as e:
                raise InvalidModelValueError(detail=e.message)

        return node


class NodeAddonSettingsSerializerBase(JSONAPISerializer):
    class Meta:
        type_ = 'node_addons'

    id = ser.CharField(source='config.short_name', read_only=True)
    node_has_auth = ser.BooleanField(source='has_auth', read_only=True)
    configured = ser.BooleanField(read_only=True)
    external_account_id = ser.CharField(source='external_account._id', required=False, allow_null=True)
    folder_id = ser.CharField(required=False, allow_null=True)
    folder_path = ser.CharField(required=False, allow_null=True)

    # Forward-specific
    label = ser.CharField(required=False, allow_null=True)
    url = ser.CharField(required=False, allow_null=True)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        kwargs = self.context['request'].parser_context['kwargs']
        if 'provider' not in kwargs or (obj and obj.config.short_name != kwargs.get('provider')):
            kwargs.update({'provider': obj.config.short_name})

        return absolute_reverse(
            'nodes:node-addon-detail',
            kwargs=kwargs
        )

    def create(self, validated_data):
        auth = Auth(self.context['request'].user)
        node = self.context['view'].get_node()
        addon = self.context['request'].parser_context['kwargs']['provider']

        return node.get_or_add_addon(addon, auth=auth)

class ForwardNodeAddonSettingsSerializer(NodeAddonSettingsSerializerBase):

    def update(self, instance, validated_data):
        auth = Auth(self.context['request'].user)
        set_url = 'url' in validated_data
        set_label = 'label' in validated_data

        url_changed = False

        url = validated_data.get('url')
        label = validated_data.get('label')

        if set_url and not url and label:
            raise exceptions.ValidationError(detail='Cannot set label without url')

        if not instance:
            node = self.context['view'].get_node()
            instance = node.get_or_add_addon('forward', auth)

        if instance and instance.url:
            # url required, label optional
            if set_url and not url:
                instance.reset()
            elif set_url and url:
                instance.url = url
                url_changed = True
            if set_label:
                instance.label = label
        elif instance and not instance.url:
            instance.url = url
            instance.label = label
            url_changed = True

        instance.save()

        if url_changed:
            # add log here because forward architecture isn't great
            # TODO [OSF-6678]: clean this up
            instance.owner.add_log(
                action='forward_url_changed',
                params=dict(
                    node=instance.owner._id,
                    project=instance.owner.parent_id,
                    forward_url=instance.url,
                ),
                auth=auth,
                save=True,
            )

        return instance


class NodeAddonSettingsSerializer(NodeAddonSettingsSerializerBase):

    def check_for_update_errors(self, node_settings, folder_info, external_account_id):
        if (not node_settings.has_auth and folder_info and not external_account_id):
            raise Conflict('Cannot set folder without authorization')

    def get_account_info(self, data):
        try:
            external_account_id = data['external_account']['_id']
            set_account = True
        except KeyError:
            external_account_id = None
            set_account = False
        return set_account, external_account_id

    def get_folder_info(self, data, addon_name):
        try:
            folder_info = data['folder_id']
            set_folder = True
        except KeyError:
            folder_info = None
            set_folder = False

        if addon_name == 'googledrive':
            folder_id = folder_info
            try:
                folder_path = data['folder_path']
            except KeyError:
                folder_path = None

            if (folder_id or folder_path) and not (folder_id and folder_path):
                raise exceptions.ValidationError(detail='Must specify both folder_id and folder_path for {}'.format(addon_name))

            folder_info = {
                'id': folder_id,
                'path': folder_path
            }
        return set_folder, folder_info

    def get_account_or_error(self, addon_name, external_account_id, auth):
            external_account = ExternalAccount.load(external_account_id)
            if not external_account:
                raise exceptions.NotFound('Unable to find requested account.')
            if external_account not in auth.user.external_accounts:
                raise exceptions.PermissionDenied('Requested action requires account ownership.')
            if external_account.provider != addon_name:
                raise Conflict('Cannot authorize the {} addon with an account for {}'.format(addon_name, external_account.provider))
            return external_account

    def should_call_set_folder(self, folder_info, instance, auth, node_settings):
        if (folder_info and not (   # If we have folder information to set
                instance and getattr(instance, 'folder_id', False) and (  # and the settings aren't already configured with this folder
                    instance.folder_id == folder_info or (hasattr(folder_info, 'get') and instance.folder_id == folder_info.get('id', False))
                ))):
            if auth.user._id != node_settings.user_settings.owner._id:  # And the user is allowed to do this
                raise exceptions.PermissionDenied('Requested action requires addon ownership.')
            return True
        return False

    def update(self, instance, validated_data):
        addon_name = instance.config.short_name
        if addon_name not in ADDONS_FOLDER_CONFIGURABLE:
            raise EndpointNotImplementedError('Requested addon not currently configurable via API.')

        auth = get_user_auth(self.context['request'])

        set_account, external_account_id = self.get_account_info(validated_data)
        set_folder, folder_info = self.get_folder_info(validated_data, addon_name)

        # Maybe raise errors
        self.check_for_update_errors(instance, folder_info, external_account_id)

        if instance and instance.configured and set_folder and not folder_info:
            # Enabled and configured, user requesting folder unset
            instance.clear_settings()
            instance.save()

        if instance and instance.has_auth and set_account and not external_account_id:
            # Settings authorized, User requesting deauthorization
            instance.deauthorize(auth=auth)  # clear_auth performs save
            return instance
        elif external_account_id:
            # Settings may or may not be authorized, user requesting to set instance.external_account
            account = self.get_account_or_error(addon_name, external_account_id, auth)
            if instance.external_account and external_account_id != instance.external_account._id:
                # Ensure node settings are deauthorized first, logs
                instance.deauthorize(auth=auth)
            instance.set_auth(account, auth.user)

        if set_folder and self.should_call_set_folder(folder_info, instance, auth, instance):
            # Enabled, user requesting to set folder
            try:
                instance.set_folder(folder_info, auth)
                instance.save()
            except InvalidFolderError:
                raise exceptions.NotFound('Unable to find requested folder.')
            except InvalidAuthError:
                raise exceptions.PermissionDenied('Addon credentials are invalid.')

        return instance


class NodeDetailSerializer(NodeSerializer):
    """
    Overrides NodeSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class NodeForksSerializer(NodeSerializer):

    category_choices = settings.NODE_CATEGORY_MAP.items()
    category_choices_string = ', '.join(["'{}'".format(choice[0]) for choice in category_choices])

    title = ser.CharField(required=False)
    category = ser.ChoiceField(read_only=True, choices=category_choices, help_text='Choices: ' + category_choices_string)
    forked_date = ser.DateTimeField(read_only=True)

    def create(self, validated_data):
        node = validated_data.pop('node')
        fork_title = validated_data.pop('title', None)
        request = self.context['request']
        auth = get_user_auth(request)
        fork = node.fork_node(auth, title=fork_title)

        try:
            fork.save()
        except ValidationValueError as e:
            raise InvalidModelValueError(detail=e.message)

        return fork


class ContributorIDField(IDField):
    """ID field to use with the contributor resource. Contributor IDs have the form "<node-id>-<user-id>"."""

    def __init__(self, *args, **kwargs):
        kwargs['source'] = kwargs.pop('source', '_id')
        kwargs['help_text'] = kwargs.get('help_text', 'Unique contributor ID. Has the form "<node-id>-<user-id>". Example: "abc12-xyz34"')
        super(ContributorIDField, self).__init__(*args, **kwargs)

    def _get_node_id(self):
        return self.context['request'].parser_context['kwargs']['node_id']

    # override IDField
    def get_id(self, obj):
        node_id = self._get_node_id()
        user_id = obj._id
        return '{}-{}'.format(node_id, user_id)

    def to_representation(self, value):
        node_id = self._get_node_id()
        user_id = super(ContributorIDField, self).to_representation(value)
        return '{}-{}'.format(node_id, user_id)


class NodeContributorsSerializer(JSONAPISerializer):
    """ Separate from UserSerializer due to necessity to override almost every field as read only
    """
    non_anonymized_fields = ['bibliographic', 'permission']
    filterable_fields = frozenset([
        'id',
        'bibliographic',
        'permission',
        'index'
    ])

    id = ContributorIDField(read_only=True, source='_id')
    type = TypeField()
    index = ser.IntegerField(required=False, read_only=True)

    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not.',
                                     default=True)
    permission = ser.ChoiceField(choices=osf_permissions.PERMISSIONS, required=False, allow_null=True,
                                 default=osf_permissions.reduce_permissions(osf_permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS),
                                 help_text='User permission level. Must be "read", "write", or "admin". Defaults to "write".')
    unregistered_contributor = ser.SerializerMethodField()

    links = LinksField({
        'self': 'get_absolute_url'
    })

    users = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<pk>'},
        always_embed=True
    )

    node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<node_id>'}
    )

    class Meta:
        type_ = 'contributors'

    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        return absolute_reverse(
            'nodes:node-contributor-detail',
            kwargs={
                'node_id': node_id,
                'user_id': obj._id
            }
        )

    def get_unregistered_contributor(self, obj):
        unclaimed_records = obj.unclaimed_records.get(obj.node_id, None)
        if unclaimed_records:
            return unclaimed_records.get('name', None)


class NodeContributorsCreateSerializer(NodeContributorsSerializer):
    """
    Overrides NodeContributorsSerializer to add email, full_name, send_email, and non-required index and users field.
    """

    id = ContributorIDField(source='_id', required=False, allow_null=True)
    full_name = ser.CharField(required=False)
    email = ser.EmailField(required=False)
    index = ser.IntegerField(required=False)

    users = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<pk>'},
        required=False
    )

    email_preferences = ['default', 'preprint', 'false']

    def validate_data(self, node, user_id=None, full_name=None, email=None, index=None):
        if user_id and (full_name or email):
            raise Conflict(detail='Full name and/or email should not be included with a user ID.')
        if not user_id and not full_name:
            raise exceptions.ValidationError(detail='A user ID or full name must be provided to add a contributor.')
        if index > len(node.contributors):
            raise exceptions.ValidationError(detail='{} is not a valid contributor index for node with id {}'.format(index, node._id))

    def create(self, validated_data):
        id = validated_data.get('_id')
        email = validated_data.get('email')
        index = validated_data.get('index')
        node = self.context['view'].get_node()
        auth = Auth(self.context['request'].user)
        full_name = validated_data.get('full_name')
        bibliographic = validated_data.get('bibliographic')
        send_email = self.context['request'].GET.get('send_email') or 'default'
        permissions = osf_permissions.expand_permissions(validated_data.get('permission')) or osf_permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS

        self.validate_data(node, user_id=id, full_name=full_name, email=email, index=index)

        if send_email not in self.email_preferences:
            raise exceptions.ValidationError(detail='{} is not a valid email preference.'.format(send_email))

        try:
            contributor = node.add_contributor_registered_or_not(
                auth=auth, user_id=id, email=email, full_name=full_name, send_email=send_email,
                permissions=permissions, bibliographic=bibliographic, index=index, save=True
            )
        except ValidationValueError as e:
            raise exceptions.ValidationError(detail=e.message)
        except ValueError as e:
            raise exceptions.NotFound(detail=e.message)

        return contributor


class NodeContributorDetailSerializer(NodeContributorsSerializer):
    """
    Overrides node contributor serializer to add additional methods
    """
    id = ContributorIDField(required=True, source='_id')
    index = ser.IntegerField(required=False, read_only=False)
    # index = ser.IntegerField(required=False)

    def update(self, instance, validated_data):
        index = None
        if 'index' in validated_data:
            index = validated_data.pop('index')

        contributor = instance
        auth = Auth(self.context['request'].user)
        node = self.context['view'].get_node()

        if 'bibliographic' in validated_data:
            bibliographic = validated_data.get('bibliographic')
        else:
            bibliographic = node.get_visible(contributor)
        permission = validated_data.get('permission') or contributor.permission
        try:
            if index is not None:
                node.move_contributor(contributor, auth, index, save=True)
            node.update_contributor(contributor, permission, bibliographic, auth, save=True)
        except NodeStateError as e:
            raise exceptions.ValidationError(detail=e.message)
        except ValueError as e:
            raise exceptions.ValidationError(detail=e.message)
        contributor.permission = osf_permissions.reduce_permissions(node.get_permissions(contributor))
        contributor.bibliographic = node.get_visible(contributor)
        contributor.node_id = node._id
        if index is not None:
            contributor.index = index
        return contributor


class NodeLinksSerializer(JSONAPISerializer):

    id = IDField(source='_id')
    type = TypeField()
    target_type = TargetTypeField(target_type='nodes')

    # TODO: We don't show the title because the current user may not have access to this node. We may want to conditionally
    # include this field in the future.
    # title = ser.CharField(read_only=True, source='node.title', help_text='The title of the node that this Node Link '
    #                                                                      'points to')

    target_node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<pk>'},
        always_embed=True

    )
    class Meta:
        type_ = 'node_links'

    links = LinksField({
        'self': 'get_absolute_url'
    })

    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        return absolute_reverse(
            'nodes:node-pointer-detail',
            kwargs={
                'node_id': node_id,
                'node_link_id': obj._id
            }
        )

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        auth = Auth(user)
        node = self.context['view'].get_node()
        target_node_id = validated_data['_id']
        pointer_node = Node.load(target_node_id)
        if not pointer_node or pointer_node.is_collection:
            raise InvalidModelValueError(
                source={'pointer': '/data/relationships/node_links/data/id'},
                detail='Target Node \'{}\' not found.'.format(target_node_id)
            )
        try:
            pointer = node.add_pointer(pointer_node, auth, save=True)
            return pointer
        except ValueError:
            raise InvalidModelValueError(
                source={'pointer': '/data/relationships/node_links/data/id'},
                detail='Target Node \'{}\' already pointed to by \'{}\'.'.format(target_node_id, node._id)
            )

    def update(self, instance, validated_data):
        pass


class NodeProviderSerializer(JSONAPISerializer):
    id = ser.SerializerMethodField(read_only=True)
    kind = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True)
    path = ser.CharField(read_only=True)
    node = ser.CharField(source='node_id', read_only=True)
    provider = ser.CharField(read_only=True)
    files = NodeFileHyperLinkField(
        related_view='nodes:node-files',
        related_view_kwargs={'node_id': '<node_id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder',
        never_embed=True
    )
    links = LinksField({
        'upload': WaterbutlerLink(),
        'new_folder': WaterbutlerLink(kind='folder'),
        'storage_addons': 'get_storage_addons_url'
    })

    class Meta:
        type_ = 'files'

    @staticmethod
    def get_id(obj):
        return '{}:{}'.format(obj.node._id, obj.provider)

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'nodes:node-provider-detail',
            kwargs={
                'node_id': obj.node._id,
                'provider': obj.provider
            }
        )

    def get_storage_addons_url(self, obj):
        return absolute_reverse(
            'addons:addon-list',
            query_kwargs={'filter[categories]': 'storage'}
        )

class InstitutionRelated(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)
    class Meta:
        type_ = 'institutions'

class NodeInstitutionsRelationshipSerializer(ser.Serializer):
    data = ser.ListField(child=InstitutionRelated())
    links = LinksField({'self': 'get_self_url',
                        'html': 'get_related_url'})

    def get_self_url(self, obj):
        return obj['self'].institutions_relationship_url()

    def get_related_url(self, obj):
        return obj['self'].institutions_url()

    class Meta:
        type_ = 'institutions'

    def get_institutions_to_add_remove(self, institutions, new_institutions):
        diff = relationship_diff(
            current_items={inst._id: inst for inst in institutions},
            new_items={inst['_id']: inst for inst in new_institutions}
        )

        insts_to_add = []
        for inst_id in diff['add']:
            inst = Institution.load(inst_id)
            if not inst:
                raise exceptions.NotFound(detail='Institution with id "{}" was not found'.format(inst_id))
            insts_to_add.append(inst)

        return insts_to_add, diff['remove'].values()

    def make_instance_obj(self, obj):
        return {
            'data': obj.affiliated_institutions,
            'self': obj
        }

    def update(self, instance, validated_data):
        node = instance['self']
        user = self.context['request'].user

        add, remove = self.get_institutions_to_add_remove(
            institutions=instance['data'],
            new_institutions=validated_data['data']
        )

        for inst in remove:
            if inst not in user.affiliated_institutions and not node.has_permission(user, 'admin'):
                raise exceptions.PermissionDenied(detail='User needs to be affiliated with {}'.format(inst.name))
            node.remove_affiliated_institution(inst, user)

        for inst in add:
            if inst not in user.affiliated_institutions:
                raise exceptions.PermissionDenied(detail='User needs to be affiliated with {}'.format(inst.name))
            node.add_affiliated_institution(inst, user)

        node.save()

        return self.make_instance_obj(node)

    def create(self, validated_data):
        instance = self.context['view'].get_object()
        user = self.context['request'].user
        node = instance['self']

        add, remove = self.get_institutions_to_add_remove(
            institutions=instance['data'],
            new_institutions=validated_data['data']
        )
        if not len(add):
            raise RelationshipPostMakesNoChanges

        for inst in add:
            if inst not in user.affiliated_institutions:
                raise exceptions.PermissionDenied(detail='User needs to be affiliated with {}'.format(inst.name))

        for inst in add:
            node.add_affiliated_institution(inst, user)
        node.save()

        return self.make_instance_obj(node)


class NodeAlternativeCitationSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    name = ser.CharField(required=True)
    text = ser.CharField(required=True)

    class Meta:
        type_ = 'citations'

    def create(self, validated_data):
        errors = self.error_checker(validated_data)
        if len(errors) > 0:
            raise exceptions.ValidationError(detail=errors)
        node = self.context['view'].get_node()
        auth = Auth(self.context['request']._user)
        citation = node.add_citation(auth, save=True, **validated_data)
        return citation

    def update(self, instance, validated_data):
        errors = self.error_checker(validated_data)
        if len(errors) > 0:
            raise exceptions.ValidationError(detail=errors)
        node = self.context['view'].get_node()
        auth = Auth(self.context['request']._user)
        instance = node.edit_citation(auth, instance, save=True, **validated_data)
        return instance

    def error_checker(self, data):
        errors = []
        name = data.get('name', None)
        text = data.get('text', None)
        citations = self.context['view'].get_node().alternative_citations
        if not (self.instance and self.instance.name == name) and citations.find(Q('name', 'eq', name)).count() > 0:
            errors.append("There is already a citation named '{}'".format(name))
        if not (self.instance and self.instance.text == text):
            matching_citations = citations.find(Q('text', 'eq', text))
            if matching_citations.count() > 0:
                names = "', '".join([str(citation.name) for citation in matching_citations])
                errors.append("Citation matches '{}'".format(names))
        return errors

    def get_absolute_url(self, obj):
        #  Citations don't have urls
        raise NotImplementedError


class DraftRegistrationSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    registration_supplement = ser.CharField(source='registration_schema._id', required=True)
    registration_metadata = ser.DictField(required=False)
    datetime_initiated = ser.DateTimeField(read_only=True)
    datetime_updated = ser.DateTimeField(read_only=True)

    branched_from = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<branched_from._id>'}
    )

    initiator = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<initiator._id>'},
    )

    registration_schema = RelationshipField(
        related_view='metaschemas:metaschema-detail',
        related_view_kwargs={'metaschema_id': '<registration_schema._id>'}
    )

    links = LinksField({
        'html': 'get_absolute_url'
    })

    def get_absolute_url(self, obj):
        return obj.absolute_url

    def create(self, validated_data):
        node = validated_data.pop('node')
        initiator = validated_data.pop('initiator')
        metadata = validated_data.pop('registration_metadata', None)

        schema_id = validated_data.pop('registration_schema').get('_id')
        schema = get_object_or_error(MetaSchema, schema_id)
        if schema.schema_version != LATEST_SCHEMA_VERSION or schema.name not in ACTIVE_META_SCHEMAS:
            raise exceptions.ValidationError('Registration supplement must be an active schema.')

        draft = DraftRegistration.create_from_node(node=node, user=initiator, schema=schema)
        reviewer = is_prereg_admin_not_project_admin(self.context['request'], draft)

        if metadata:
            try:
                # Required fields are only required when creating the actual registration, not updating the draft.
                draft.validate_metadata(metadata=metadata, reviewer=reviewer, required_fields=False)
            except ValidationValueError as e:
                raise exceptions.ValidationError(e.message)
            draft.update_metadata(metadata)
            draft.save()
        return draft

    class Meta:
        type_ = 'draft_registrations'


class DraftRegistrationDetailSerializer(DraftRegistrationSerializer):
    """
    Overrides DraftRegistrationSerializer to make id and registration_metadata required.
    registration_supplement cannot be changed after draft has been created.

    Also makes registration_supplement read-only.
    """
    id = IDField(source='_id', required=True)
    registration_metadata = ser.DictField(required=True)
    registration_supplement = ser.CharField(read_only=True, source='registration_schema._id')

    def update(self, draft, validated_data):
        """
        Update draft instance with the validated metadata.
        """
        metadata = validated_data.pop('registration_metadata', None)
        reviewer = is_prereg_admin_not_project_admin(self.context['request'], draft)
        if metadata:
            try:
                # Required fields are only required when creating the actual registration, not updating the draft.
                draft.validate_metadata(metadata=metadata, reviewer=reviewer, required_fields=False)
            except ValidationValueError as e:
                raise exceptions.ValidationError(e.message)
            draft.update_metadata(metadata)
            draft.save()
        return draft


class NodeVOL(ser.Field):
    def to_representation(self, obj):
        if obj is not None:
            return obj._id
        return None

    def to_internal_value(self, data):
        return data


class NodeViewOnlyLinkSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'anonymous',
        'name',
        'date_created'
    ])

    key = ser.CharField(read_only=True)
    id = IDField(source='_id', read_only=True)
    date_created = ser.DateTimeField(read_only=True)
    anonymous = ser.BooleanField(required=False, default=False)
    name = ser.CharField(required=False, default='Shared project link')

    links = LinksField({
        'self': 'get_absolute_url'
    })

    creator = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
    )

    nodes = RelationshipField(
        related_view='view-only-links:view-only-link-nodes',
        related_view_kwargs={'link_id': '<_id>'},
        self_view='view-only-links:view-only-link-nodes-relationships',
        self_view_kwargs={'link_id': '<_id>'}
    )

    def create(self, validated_data):
        name = validated_data.pop('name')
        user = get_user_auth(self.context['request']).user
        anonymous = validated_data.pop('anonymous')
        node = self.context['view'].get_node()

        try:
            view_only_link = new_private_link(
                name=name,
                user=user,
                nodes=[node],
                anonymous=anonymous
            )
        except ValidationValueError:
            raise exceptions.ValidationError('Invalid link name.')

        return view_only_link

    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        return absolute_reverse(
            'nodes:node-view-only-link-detail',
            kwargs={
                'link_id': obj._id,
                'node_id': node_id
            }
        )

    class Meta:
        type_ = 'view_only_links'


class NodeViewOnlyLinkUpdateSerializer(NodeViewOnlyLinkSerializer):
    """
    Overrides NodeViewOnlyLinkSerializer to not default name and anonymous on update.
    """
    name = ser.CharField(required=False)
    anonymous = ser.BooleanField(required=False)

    def update(self, link, validated_data):
        assert isinstance(link, PrivateLink), 'link must be a PrivateLink'

        name = validated_data.get('name')
        anonymous = validated_data.get('anonymous')

        if name:
            link.name = name
        if anonymous:
            link.anonymous = anonymous

        link.save()
        return link
