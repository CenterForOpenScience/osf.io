import json

from modularodm.exceptions import ValidationValueError

from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.utils import absolute_reverse, get_user_auth
from website.project.metadata.utils import is_prereg_admin_not_project_admin
from website.exceptions import NodeStateError
from website.project.model import NodeUpdateError

from api.files.serializers import FileSerializer
from api.nodes.serializers import NodeSerializer, NodeProviderSerializer
from api.nodes.serializers import NodeLinksSerializer, NodeLicenseSerializer
from api.nodes.serializers import NodeContributorsSerializer, NodeTagField
from api.base.serializers import (IDField, RelationshipField, LinksField, HideIfWithdrawal,
                                  FileCommentRelationshipField, NodeFileHyperLinkField, HideIfRegistration, JSONAPIListField)


class BaseRegistrationSerializer(NodeSerializer):

    title = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    category_choices = NodeSerializer.category_choices
    category_choices_string = NodeSerializer.category_choices_string
    category = HideIfWithdrawal(ser.ChoiceField(read_only=True, choices=category_choices, help_text='Choices: ' + category_choices_string))

    date_modified = HideIfWithdrawal(ser.DateTimeField(read_only=True))
    fork = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_fork'))
    collection = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_collection'))
    node_license = HideIfWithdrawal(NodeLicenseSerializer(read_only=True))
    tags = HideIfWithdrawal(JSONAPIListField(child=NodeTagField(), read_only=True))
    public = HideIfWithdrawal(ser.BooleanField(source='is_public', required=False,
                                               help_text='Nodes that are made public will give read-only access '
                                        'to everyone. Private nodes require explicit read '
                                        'permission. Write and admin access are the same for '
                                        'public and private nodes. Administrators on a parent '
                                        'node have implicit read permissions for all child nodes'))
    current_user_permissions = HideIfWithdrawal(ser.SerializerMethodField(help_text='List of strings representing the permissions '
                                                                   'for the current user on this node.'))
    inherit_contributors = ser.BooleanField(read_only=True)

    pending_embargo_approval = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_pending_embargo',
                                                                 help_text='The associated Embargo is awaiting approval by project admins.'))
    pending_registration_approval = HideIfWithdrawal(ser.BooleanField(source='is_pending_registration', read_only=True,
                                                                      help_text='The associated RegistrationApproval is awaiting approval by project admins.'))
    pending_withdrawal = HideIfWithdrawal(ser.BooleanField(source='is_pending_retraction', read_only=True,
                                                           help_text='The registration is awaiting withdrawal approval by project admins.'))
    withdrawn = ser.BooleanField(source='is_retracted', read_only=True,
                                 help_text='The registration has been withdrawn.')

    date_registered = ser.DateTimeField(source='registered_date', read_only=True, help_text='Date time of registration.')
    embargo_end_date = HideIfWithdrawal(ser.SerializerMethodField(help_text='When the embargo on this registration will be lifted.'))

    withdrawal_justification = ser.CharField(source='retraction.justification', read_only=True)
    template_from = HideIfWithdrawal(ser.CharField(read_only=True, allow_blank=False, allow_null=False,
                help_text='Specify a node id for a node you would like to use as a template for the '
                'new node. Templating is like forking, except that you do not copy the '
                'files, only the project structure. Some information is changed on the top '
                'level project by submitting the appropriate fields in the request body, '
                'and some information will not change. By default, the description will '
                'be cleared and the project will be made private.'))
    registration_supplement = ser.SerializerMethodField()
    registered_meta = HideIfWithdrawal(ser.SerializerMethodField(
        help_text='A dictionary with supplemental registration questions and responses.'))

    registered_by = HideIfWithdrawal(RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<registered_user_id>'}
    ))

    registered_from = HideIfWithdrawal(RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<registered_from_id>'}
    ))

    children = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-children',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_node_count'},
    ))

    comments = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-comments',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'unread': 'get_unread_comments_count'},
        filter={'target': '<pk>'}
    ))

    contributors = RelationshipField(
        related_view='registrations:registration-contributors',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_contrib_count'}
    )

    files = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-providers',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    wikis = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-wikis',
        related_view_kwargs={'node_id': '<pk>'},
    ))

    forked_from = HideIfWithdrawal(RelationshipField(
        related_view=lambda n: 'registrations:registration-detail' if getattr(n, 'is_registration', False) else 'nodes:node-detail',
        related_view_kwargs={'node_id': '<forked_from_id>'}
    ))

    license = HideIfWithdrawal(RelationshipField(
        related_view='licenses:license-detail',
        related_view_kwargs={'license_id': '<node_license.node_license._id>'},
    ))

    logs = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-logs',
        related_view_kwargs={'node_id': '<pk>'},
    ))

    forks = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-forks',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    node_links = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-pointers',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_pointers_count'}
    ))

    parent = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<parent_node._id>'},
        filter_key='parent_node'
    ))

    root = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<root._id>'}
    ))

    affiliated_institutions = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-institutions',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    registration_schema = RelationshipField(
        related_view='metaschemas:metaschema-detail',
        related_view_kwargs={'metaschema_id': '<registered_schema_id>'}
    )

    registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-registrations',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    draft_registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-draft-registrations',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    identifiers = HideIfWithdrawal(RelationshipField(
        related_view='registrations:identifier-list',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    links = LinksField({'self': 'get_registration_url', 'html': 'get_absolute_html_url'})

    def get_registration_url(self, obj):
        return absolute_reverse('registrations:registration-detail', kwargs={'node_id': obj._id})

    def get_absolute_url(self, obj):
        return self.get_registration_url(obj)

    def create(self, validated_data):
        auth = get_user_auth(self.context['request'])
        draft = validated_data.pop('draft')
        registration_choice = validated_data.pop('registration_choice', 'immediate')
        embargo_lifted = validated_data.pop('lift_embargo', None)
        reviewer = is_prereg_admin_not_project_admin(self.context['request'], draft)

        try:
            draft.validate_metadata(metadata=draft.registration_metadata, reviewer=reviewer, required_fields=True)
        except ValidationValueError as e:
            raise exceptions.ValidationError(e.message)

        registration = draft.register(auth, save=True)

        if registration_choice == 'embargo':
            if not embargo_lifted:
                raise exceptions.ValidationError('lift_embargo must be specified.')
            embargo_end_date = embargo_lifted.replace(tzinfo=None)
            try:
                registration.embargo_registration(auth.user, embargo_end_date)
            except ValidationValueError as err:
                raise exceptions.ValidationError(err.message)
        else:
            try:
                registration.require_approval(auth.user)
            except NodeStateError as err:
                raise exceptions.ValidationError(err)

        registration.save()
        return registration

    def get_registered_meta(self, obj):
        if obj.registered_meta:
            meta_values = obj.registered_meta.values()[0]
            try:
                return json.loads(meta_values)
            except TypeError:
                return meta_values
            except ValueError:
                return meta_values
        return None

    def get_embargo_end_date(self, obj):
        if obj.embargo_end_date:
            return obj.embargo_end_date
        return None

    def get_registration_supplement(self, obj):
        if obj.registered_schema:
            schema = obj.registered_schema[0]
            if schema is None:
                return None
            return schema.name
        return None

    def get_current_user_permissions(self, obj):
        return NodeSerializer.get_current_user_permissions(self, obj)

    def update(self, registration, validated_data):
        is_public = validated_data.get('is_public', False)
        if is_public:
            try:
                registration.update(validated_data)
            except NodeUpdateError as err:
                raise exceptions.ValidationError(err.reason)
        else:
            raise exceptions.ValidationError('Registrations can only be turned from private to public.')
        return registration

    class Meta:
        type_ = 'registrations'


class RegistrationSerializer(BaseRegistrationSerializer):
    """
    Overrides BaseRegistrationSerializer to add draft_registration, registration_choice, and lift_embargo fields
    """
    draft_registration = ser.CharField(write_only=True)
    registration_choice = ser.ChoiceField(write_only=True, choices=['immediate', 'embargo'])
    lift_embargo = ser.DateTimeField(write_only=True, default=None, input_formats=['%Y-%m-%dT%H:%M:%S'])


class RegistrationDetailSerializer(BaseRegistrationSerializer):
    """
    Overrides BaseRegistrationSerializer to make id required.
    """

    id = IDField(source='_id', required=True)


class RegistrationNodeLinksSerializer(NodeLinksSerializer):
    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        return absolute_reverse(
            'registrations:registration-pointer-detail',
            kwargs={
                'node_id': node_id,
                'node_link_id': obj._id
            }
        )


class RegistrationContributorsSerializer(NodeContributorsSerializer):
    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        return absolute_reverse(
            'registrations:registration-contributor-detail',
            kwargs={
                'node_id': node_id,
                'user_id': obj._id
            }
        )


class RegistrationFileSerializer(FileSerializer):

    files = NodeFileHyperLinkField(
        related_view='registrations:registration-files',
        related_view_kwargs={'node_id': '<node_id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder'
    )

    comments = FileCommentRelationshipField(related_view='registrations:registration-comments',
                                            related_view_kwargs={'node_id': '<node._id>'},
                                            related_meta={'unread': 'get_unread_comments_count'},
                                            filter={'target': 'get_file_guid'})


class RegistrationProviderSerializer(NodeProviderSerializer):
    """
    Overrides NodeProviderSerializer to lead to correct registration file links
    """
    files = NodeFileHyperLinkField(
        related_view='registrations:registration-files',
        related_view_kwargs={'node_id': '<node_id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder',
        never_embed=True
    )
