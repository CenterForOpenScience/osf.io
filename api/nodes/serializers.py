from django.db import connection
from distutils.version import StrictVersion

from api.base.exceptions import (
    Conflict, EndpointNotImplementedError,
    InvalidModelValueError,
    RelationshipPostMakesNoChanges,
)
from api.base.serializers import (
    VersionedDateTimeField, HideIfRegistration, IDField,
    JSONAPIRelationshipSerializer,
    JSONAPISerializer, LinksField,
    NodeFileHyperLinkField, RelationshipField,
    ShowIfVersion, TargetTypeField, TypeField,
    WaterbutlerLink, relationship_diff, BaseAPISerializer,
    HideIfWikiDisabled, ShowIfAdminScopeOrAnonymous,
    ValuesListField,
)
from api.base.settings import ADDONS_FOLDER_CONFIGURABLE
from api.base.utils import (
    absolute_reverse, get_object_or_error,
    get_user_auth, is_truthy,
)
from api.taxonomies.serializers import TaxonomizableSerializerMixin
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from osf.models import Tag
from rest_framework import serializers as ser
from rest_framework import exceptions
from addons.base.exceptions import InvalidAuthError, InvalidFolderError
from addons.osfstorage.models import Region
from osf.exceptions import NodeStateError
from osf.models import (
    Comment, DraftRegistration, Institution,
    RegistrationSchema, AbstractNode, PrivateLink,
    RegistrationProvider, OSFGroup,
)
from osf.models.external import ExternalAccount
from osf.models.licenses import NodeLicense
from osf.models.preprint import Preprint
from website.project import new_private_link
from website.project.metadata.utils import is_prereg_admin_not_project_admin
from website.project.model import NodeUpdateError
from osf.utils import permissions as osf_permissions


class RegistrationProviderRelationshipField(RelationshipField):
    def get_object(self, _id):
        return RegistrationProvider.load(_id)

    def to_internal_value(self, data):
        provider = self.get_object(data)
        return {'provider': provider}


def get_or_add_license_to_serializer_context(serializer, node):
    """
    Returns license, and adds license to serializer context with format
    serializer.context['licenses'] = {<node_id>: <NodeLicenseRecord object>}

    Used for both node_license field and license relationship in the NodeSerializer.
    Prevents license from having to be fetched 2x per node.
    """
    license_context = serializer.context.get('licenses', {})
    if license_context and node._id in license_context:
        return license_context.get(node._id)
    else:
        license = node.license
        if license_context:
            license_context[node._id] = {}
            license_context[node._id] = license
        else:
            serializer.context['licenses'] = {}
            serializer.context['licenses'][node._id] = license
        return license


def get_institutions_to_add_remove(institutions, new_institutions):
    diff = relationship_diff(
        current_items={inst._id: inst for inst in institutions.all()},
        new_items={inst['_id']: inst for inst in new_institutions},
    )

    insts_to_add = []
    for inst_id in diff['add']:
        inst = Institution.load(inst_id)
        if not inst:
            raise exceptions.NotFound(detail='Institution with id "{}" was not found'.format(inst_id))
        insts_to_add.append(inst)

    return insts_to_add, diff['remove'].values()


def update_institutions(node, new_institutions, user, post=False):
    add, remove = get_institutions_to_add_remove(
        institutions=node.affiliated_institutions,
        new_institutions=new_institutions,
    )

    if post and not len(add):
        raise RelationshipPostMakesNoChanges

    if not post:
        for inst in remove:
            if not user.is_affiliated_with_institution(inst) and not node.has_permission(user, osf_permissions.ADMIN):
                raise exceptions.PermissionDenied(
                    detail='User needs to be affiliated with {}'.format(inst.name),
                )
            node.remove_affiliated_institution(inst, user)

    for inst in add:
        if not user.is_affiliated_with_institution(inst):
            raise exceptions.PermissionDenied(
                detail='User needs to be affiliated with {}'.format(inst.name),
            )
        node.add_affiliated_institution(inst, user)


class RegionRelationshipField(RelationshipField):

    def to_internal_value(self, data):
        try:
            region_id = Region.objects.filter(_id=data).values_list('id', flat=True).get()
        except Region.DoesNotExist:
            raise exceptions.ValidationError(detail='Region {} is invalid.'.format(data))
        return {'region_id': region_id}


class NodeTagField(ser.Field):
    def to_representation(self, obj):
        if obj is not None:
            return obj.name
        return None

    def to_internal_value(self, data):
        return data


class NodeLicenseSerializer(BaseAPISerializer):

    copyright_holders = ser.ListField(allow_empty=True, required=False)
    year = ser.CharField(allow_blank=True, required=False)

    class Meta:
        type_ = 'node_licenses'

    def get_attribute(self, instance):
        """
        Returns node license and caches license in serializer context for optimization purposes.
        """
        return get_or_add_license_to_serializer_context(self, instance)


class NodeLicenseRelationshipField(RelationshipField):

    def lookup_attribute(self, obj, lookup_field):
        """
        Returns node license id and caches license in serializer context for optimization purposes.
        """
        license = get_or_add_license_to_serializer_context(self, obj)
        return license.node_license._id if getattr(license, 'node_license', None) else None

    def to_internal_value(self, license_id):
        node_license = NodeLicense.load(license_id)
        if node_license:
            return {'license_type': node_license}
        raise exceptions.NotFound('Unable to find specified license.')


class NodeCitationSerializer(JSONAPISerializer):
    non_anonymized_fields = [
        'doi',
        'id',
        'links',
        'publisher',
        'title',
        'type',
    ]
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

def get_license_details(node, validated_data):
    if node:
        license = node.license if isinstance(node, Preprint) else node.node_license
    else:
        license = None
    if ('license_type' not in validated_data and not (license and license.node_license.license_id)):
        raise exceptions.ValidationError(detail='License ID must be provided for a Node License.')
    license_id = license.node_license.license_id if license else None
    license_year = license.year if license else None
    license_holders = license.copyright_holders if license else []

    if 'license' in validated_data:
        license_year = validated_data['license'].get('year', license_year)
        license_holders = validated_data['license'].get('copyright_holders', license_holders)
    if 'license_type' in validated_data:
        license_id = validated_data['license_type'].license_id

    return {
        'id': license_id,
        'year': license_year,
        'copyrightHolders': license_holders,
    }

class NodeSerializer(TaxonomizableSerializerMixin, JSONAPISerializer):
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
        'preprint',
        'subjects',
    ])

    # If you add a field to this serializer, be sure to add to this
    # list if it doesn't expose user data
    non_anonymized_fields = [
        'access_requests_enabled',
        'affiliated_institutions',
        'analytics_key',
        'category',
        'children',
        'collection',
        'comments',
        'current_user_is_contributor',
        'current_user_is_contributor_or_group_member',
        'current_user_permissions',
        'date_created',
        'date_modified',
        'description',
        'draft_registrations',
        'files',
        'fork',
        'forked_from',
        'id',
        'identifiers',
        'license',
        'linked_by_nodes',
        'linked_by_registrations',
        'linked_nodes',
        'linked_registrations',
        'links',
        'logs',
        'node_links',
        'parent',
        'preprint',
        'preprints',
        'public',
        'region',
        'registration',
        'root',
        'settings',
        'subjects',
        'tags',
        'template_from',
        'template_node',
        'title',
        'type',
        'view_only_links',
        'wiki_enabled',
        'wikis',
    ]

    id = IDField(source='_id', read_only=True)
    type = TypeField()

    category_choices = settings.NODE_CATEGORY_MAP.items()
    category_choices_string = ', '.join(["'{}'".format(choice[0]) for choice in category_choices])

    title = ser.CharField(required=True)
    description = ser.CharField(required=False, allow_blank=True, allow_null=True)
    category = ser.ChoiceField(choices=category_choices, help_text='Choices: ' + category_choices_string)
    custom_citation = ser.CharField(allow_blank=True, required=False)
    date_created = VersionedDateTimeField(source='created', read_only=True)
    date_modified = VersionedDateTimeField(source='last_logged', read_only=True)
    registration = ser.BooleanField(read_only=True, source='is_registration')
    preprint = ser.SerializerMethodField()
    fork = ser.BooleanField(read_only=True, source='is_fork')
    collection = ser.BooleanField(read_only=True, source='is_collection')
    tags = ValuesListField(attr_name='name', child=ser.CharField(), required=False)
    access_requests_enabled = ShowIfVersion(ser.BooleanField(read_only=False, required=False), min_version='2.0', max_version='2.8')
    node_license = NodeLicenseSerializer(required=False, source='license')
    analytics_key = ShowIfAdminScopeOrAnonymous(ser.CharField(read_only=True, source='keenio_read_key'))
    template_from = ser.CharField(
        required=False, allow_blank=False, allow_null=False,
        help_text='Specify a node id for a node you would like to use as a template for the '
                  'new node. Templating is like forking, except that you do not copy the '
                  'files, only the project structure. Some information is changed on the top '
                  'level project by submitting the appropriate fields in the request body, '
                  'and some information will not change. By default, the description will '
                  'be cleared and the project will be made private.',
    )
    current_user_can_comment = ser.SerializerMethodField(help_text='Whether the current user is allowed to post comments')
    current_user_permissions = ser.SerializerMethodField(
        help_text='List of strings representing the permissions '
        'for the current user on this node. As of version 2.11, this field will only return the permissions '
        'explicitly assigned to the current user, and will not automatically return read for all public nodes',
    )
    current_user_is_contributor = ser.SerializerMethodField(
        help_text='Whether the current user is a contributor on this node.',
    )
    current_user_is_contributor_or_group_member = ser.SerializerMethodField(
        help_text='Whether the current user is a contributor or group member on this node.',
    )
    wiki_enabled = ser.SerializerMethodField(help_text='Whether the wiki addon is enabled')

    # Public is only write-able by admins--see update method
    public = ser.BooleanField(
        source='is_public', required=False,
        help_text='Nodes that are made public will give read-only access '
                  'to everyone. Private nodes require explicit read '
                  'permission. Write and admin access are the same for '
                  'public and private nodes. Administrators on a parent '
                  'node have implicit read permissions for all child nodes',
    )

    links = LinksField({'html': 'get_absolute_html_url'})
    # TODO: When we have osf_permissions.ADMIN permissions, make this writable for admins

    license = NodeLicenseRelationshipField(
        related_view='licenses:license-detail',
        related_view_kwargs={'license_id': '<license.node_license._id>'},
        read_only=False,
    )

    children = RelationshipField(
        related_view='nodes:node-children',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_node_count'},
    )

    comments = RelationshipField(
        related_view='nodes:node-comments',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'unread': 'get_unread_comments_count'},
        filter={'target': '<_id>'},
    )

    contributors = RelationshipField(
        related_view='nodes:node-contributors',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_contrib_count'},
    )

    bibliographic_contributors = RelationshipField(
        related_view='nodes:node-bibliographic-contributors',
        related_view_kwargs={'node_id': '<_id>'},
    )

    implicit_contributors = RelationshipField(
        related_view='nodes:node-implicit-contributors',
        related_view_kwargs={'node_id': '<_id>'},
        help_text='This feature is experimental and being tested. It may be deprecated.',
    )

    files = RelationshipField(
        related_view='nodes:node-storage-providers',
        related_view_kwargs={'node_id': '<_id>'},
    )

    settings = RelationshipField(
        related_view='nodes:node-settings',
        related_view_kwargs={'node_id': '<_id>'},
    )

    wikis = HideIfWikiDisabled(RelationshipField(
        related_view='nodes:node-wikis',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_wiki_page_count'},
    ))

    forked_from = RelationshipField(
        related_view=lambda n: 'registrations:registration-detail' if getattr(n, 'is_registration', False) else 'nodes:node-detail',
        related_view_kwargs={'node_id': '<forked_from_guid>'},
    )

    template_node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<template_node._id>'},
    )

    forks = RelationshipField(
        related_view='nodes:node-forks',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_forks_count'},
    )

    groups = RelationshipField(
        related_view='nodes:node-groups',
        related_view_kwargs={'node_id': '<_id>'},
    )

    node_links = ShowIfVersion(
        RelationshipField(
            related_view='nodes:node-pointers',
            related_view_kwargs={'node_id': '<_id>'},
            related_meta={'count': 'get_pointers_count'},
            help_text='This feature is deprecated as of version 2.1. Use linked_nodes instead.',
        ), min_version='2.0', max_version='2.0',
    )

    linked_by_nodes = RelationshipField(
        related_view='nodes:node-linked-by-nodes',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_linked_by_nodes_count'},
    )

    linked_by_registrations = RelationshipField(
        related_view='nodes:node-linked-by-registrations',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_linked_by_registrations_count'},
    )

    parent = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<parent_id>'},
        filter_key='parent_node',
    )

    identifiers = RelationshipField(
        related_view='nodes:identifier-list',
        related_view_kwargs={'node_id': '<_id>'},
    )

    draft_registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-draft-registrations',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_draft_registration_count'},
    ))

    registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-registrations',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_registration_count'},
    ))

    region = RegionRelationshipField(
        related_view='regions:region-detail',
        related_view_kwargs={'region_id': 'get_region_id'},
        read_only=False,
    )

    affiliated_institutions = RelationshipField(
        related_view='nodes:node-institutions',
        related_view_kwargs={'node_id': '<_id>'},
        self_view='nodes:node-relationships-institutions',
        self_view_kwargs={'node_id': '<_id>'},
        read_only=False,
        many=True,
        required=False,
    )

    root = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<root._id>'},
    )

    logs = RelationshipField(
        related_view='nodes:node-logs',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_logs_count'},
    )

    linked_nodes = RelationshipField(
        related_view='nodes:linked-nodes',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_node_links_count'},
        self_view='nodes:node-pointer-relationship',
        self_view_kwargs={'node_id': '<_id>'},
        self_meta={'count': 'get_node_links_count'},
    )

    linked_registrations = RelationshipField(
        related_view='nodes:linked-registrations',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_registration_links_count'},
        self_view='nodes:node-registration-pointer-relationship',
        self_view_kwargs={'node_id': '<_id>'},
        self_meta={'count': 'get_node_links_count'},
    )

    view_only_links = RelationshipField(
        related_view='nodes:node-view-only-links',
        related_view_kwargs={'node_id': '<_id>'},
    )

    citation = RelationshipField(
        related_view='nodes:node-citation',
        related_view_kwargs={'node_id': '<_id>'},
    )

    preprints = HideIfRegistration(RelationshipField(
        related_view='nodes:node-preprints',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    @property
    def subjects_related_view(self):
        # Overrides TaxonomizableSerializerMixin
        return 'nodes:node-subjects'

    @property
    def subjects_view_kwargs(self):
        # Overrides TaxonomizableSerializerMixin
        return {'node_id': '<_id>'}

    @property
    def subjects_self_view(self):
        # Overrides TaxonomizableSerializerMixin
        return 'nodes:node-relationships-subjects'

    def get_current_user_permissions(self, obj):
        """
        Returns the logged-in user's permissions to the
        current node.  Implicit admin factored in.
        Can have contributor or group member permissions.
        """
        user = self.context['request'].user
        request_version = self.context['request'].version
        default_perm = [osf_permissions.READ] if StrictVersion(request_version) < StrictVersion('2.11') else []
        if user.is_anonymous:
            return default_perm

        if hasattr(obj, 'has_admin'):
            user_perms = []
            if obj.has_admin:
                user_perms = [osf_permissions.ADMIN, osf_permissions.WRITE, osf_permissions.READ]
            elif obj.has_write:
                user_perms = [osf_permissions.WRITE, osf_permissions.READ]
            elif obj.has_read:
                user_perms = [osf_permissions.READ]
        else:
            user_perms = obj.get_permissions(user)[::-1]

        user_perms = user_perms or default_perm
        if not user_perms and user in obj.parent_admin_users:
            user_perms = [osf_permissions.READ]
        return user_perms

    def get_current_user_can_comment(self, obj):
        user = self.context['request'].user
        auth = Auth(user if not user.is_anonymous else None)

        if hasattr(obj, 'has_read'):
            if obj.comment_level == 'public':
                return auth.logged_in and (
                    obj.is_public or
                    (auth.user and obj.has_read)
                )
            return obj.has_read or False
        else:
            return obj.can_comment(auth)

    def get_preprint(self, obj):
        # Whether the node has supplemental material for a preprint the user can view
        if hasattr(obj, 'has_viewable_preprints'):
            # if queryset has been annotated with "has_viewable_preprints", use this value
            return obj.has_viewable_preprints
        else:
            user = self.context['request'].user
            return Preprint.objects.can_view(base_queryset=obj.preprints, user=user).exists()

    def get_current_user_is_contributor(self, obj):
        # Returns whether user is a contributor (does not include group members)
        if hasattr(obj, 'user_is_contrib'):
            return obj.user_is_contrib

        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return obj.is_contributor(user)

    def get_current_user_is_contributor_or_group_member(self, obj):
        # Returns whether user is a contributor -or- a group member
        if hasattr(obj, 'has_read'):
            return obj.has_read

        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return obj.is_contributor_or_group_member(user)

    class Meta:
        type_ = 'nodes'

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    # TODO: See if we can get the count filters into the filter rather than the serializer.

    def get_logs_count(self, obj):
        return obj.logs.count()

    def get_node_count(self, obj):
        """
        Returns the count of a node's direct children that the user has permission to view.
        Implict admin and group membership are factored in when determining perms.
        """
        auth = get_user_auth(self.context['request'])
        user_id = getattr(auth.user, 'id', None)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH RECURSIVE parents AS (
                  SELECT parent_id, child_id
                  FROM osf_noderelation
                  WHERE child_id = %s AND is_node_link IS FALSE
                UNION ALL
                  SELECT osf_noderelation.parent_id, parents.parent_id AS child_id
                  FROM parents JOIN osf_noderelation ON parents.PARENT_ID = osf_noderelation.child_id
                  WHERE osf_noderelation.is_node_link IS FALSE
                ), has_admin AS (SELECT EXISTS(
                    SELECT P.codename
                    FROM auth_permission AS P
                    INNER JOIN osf_nodegroupobjectpermission AS G ON (P.id = G.permission_id)
                    INNER JOIN osf_osfuser_groups AS UG ON (G.group_id = UG.group_id)
                    WHERE (P.codename = 'admin_node'
                           AND (G.content_object_id IN (
                                SELECT parent_id
                                FROM parents
                           ) OR G.content_object_id = %s)
                           AND UG.osfuser_id = %s)
                ))
                SELECT COUNT(DISTINCT child_id)
                FROM
                  osf_noderelation
                JOIN osf_abstractnode ON osf_noderelation.child_id = osf_abstractnode.id
                LEFT JOIN osf_privatelink_nodes ON osf_abstractnode.id = osf_privatelink_nodes.abstractnode_id
                LEFT JOIN osf_privatelink ON osf_privatelink_nodes.privatelink_id = osf_privatelink.id
                WHERE parent_id = %s AND is_node_link IS FALSE
                AND osf_abstractnode.is_deleted IS FALSE
                AND (
                  osf_abstractnode.is_public
                  OR (SELECT exists from has_admin) = TRUE
                  OR (SELECT EXISTS(
                      SELECT P.codename
                      FROM auth_permission AS P
                      INNER JOIN osf_nodegroupobjectpermission AS G ON (P.id = G.permission_id)
                      INNER JOIN osf_osfuser_groups AS UG ON (G.group_id = UG.group_id)
                      WHERE (P.codename = 'read_node'
                             AND G.content_object_id = osf_abstractnode.id
                             AND UG.osfuser_id = %s)
                      )
                  )
                  OR (osf_privatelink.key = %s AND osf_privatelink.is_deleted = FALSE)
                );
            """, [obj.id, obj.id, user_id, obj.id, user_id, auth.private_key],
            )

            return int(cursor.fetchone()[0])

    def get_contrib_count(self, obj):
        return len(obj.contributors)

    def get_registration_count(self, obj):
        auth = get_user_auth(self.context['request'])
        registrations = [node for node in obj.registrations_all if node.can_view(auth)]
        return len(registrations)

    def get_draft_registration_count(self, obj):
        auth = get_user_auth(self.context['request'])
        if obj.has_permission(auth.user, osf_permissions.ADMIN):
            return obj.draft_registrations_active.count()

    def get_pointers_count(self, obj):
        return obj.linked_nodes.count()

    def get_wiki_page_count(self, obj):
        return obj.wikis.filter(deleted__isnull=True).count()

    def get_node_links_count(self, obj):
        auth = get_user_auth(self.context['request'])
        linked_nodes = obj.linked_nodes.filter(is_deleted=False).exclude(type='osf.collection').exclude(type='osf.registration')
        return linked_nodes.can_view(auth.user, auth.private_link).count()

    def get_registration_links_count(self, obj):
        auth = get_user_auth(self.context['request'])
        linked_registrations = obj.linked_nodes.filter(is_deleted=False, type='osf.registration').exclude(type='osf.collection')
        return linked_registrations.can_view(auth.user, auth.private_link).count()

    def get_linked_by_nodes_count(self, obj):
        return obj._parents.filter(is_node_link=True, parent__is_deleted=False, parent__type='osf.node').count()

    def get_linked_by_registrations_count(self, obj):
        return obj._parents.filter(is_node_link=True, parent__type='osf.registration', parent__retraction__isnull=True).count()

    def get_forks_count(self, obj):
        return obj.forks.exclude(type='osf.registration').exclude(is_deleted=True).count()

    def get_unread_comments_count(self, obj):
        user = get_user_auth(self.context['request']).user
        node_comments = Comment.find_n_unread(user=user, node=obj, page='node')

        return {
            'node': node_comments,
        }

    def get_region_id(self, obj):
        try:
            # use the annotated value if possible
            region_id = obj.region
        except AttributeError:
            # use computed property if region annotation does not exist
            # i.e. after creating a node
            region_id = obj.osfstorage_region._id
        return region_id

    def get_wiki_enabled(self, obj):
        return obj.has_wiki_addon if hasattr(obj, 'has_wiki_addon') else obj.has_addon('wiki')

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        Node = apps.get_model('osf.Node')
        tag_instances = []
        affiliated_institutions = None
        region_id = None
        license_details = None
        if 'affiliated_institutions' in validated_data:
            affiliated_institutions = validated_data.pop('affiliated_institutions')
        if 'region_id' in validated_data:
            region_id = validated_data.pop('region_id')
        if 'license_type' in validated_data or 'license' in validated_data:
            try:
                license_details = get_license_details(None, validated_data)
            except ValidationError as e:
                raise InvalidModelValueError(detail=str(e.messages[0]))
            validated_data.pop('license', None)
            validated_data.pop('license_type', None)
        if 'tags' in validated_data:
            tags = validated_data.pop('tags')
            for tag in tags:
                tag_instance, created = Tag.objects.get_or_create(name=tag, defaults=dict(system=False))
                tag_instances.append(tag_instance)
        if 'template_from' in validated_data:
            template_from = validated_data.pop('template_from')
            template_node = Node.load(template_from)
            if template_node is None:
                raise exceptions.NotFound
            if not template_node.has_permission(user, osf_permissions.READ, check_parent=False):
                raise exceptions.PermissionDenied
            validated_data.pop('creator')
            changed_data = {template_from: validated_data}
            node = template_node.use_as_template(auth=get_user_auth(request), changes=changed_data)
        else:
            node = Node(**validated_data)
        try:
            node.save()
        except ValidationError as e:
            raise InvalidModelValueError(detail=e.messages[0])
        if affiliated_institutions:
            new_institutions = [{'_id': institution} for institution in affiliated_institutions]
            update_institutions(node, new_institutions, user, post=True)
            node.save()
        if len(tag_instances):
            for tag in tag_instances:
                node.tags.add(tag)
        if is_truthy(request.GET.get('inherit_contributors')) and validated_data['parent'].has_permission(user, osf_permissions.WRITE):
            auth = get_user_auth(request)
            parent = validated_data['parent']
            contributors = []
            for contributor in parent.contributor_set.exclude(user=user):
                contributors.append({
                    'user': contributor.user,
                    'permissions': contributor.permission,
                    'visible': contributor.visible,
                })
                if not contributor.user.is_registered:
                    try:
                        node.add_unregistered_contributor(
                            fullname=contributor.user.fullname, email=contributor.user.email, auth=auth,
                            permissions=contributor.permission, existing_user=contributor.user,
                        )
                    except ValidationError as e:
                        raise InvalidModelValueError(detail=str(e[0]))
            node.add_contributors(contributors, auth=auth, log=True, save=True)
            for group in parent.osf_groups:
                if group.is_manager(user):
                    node.add_osf_group(group, group.get_permission_to_node(parent), auth=auth)
        if is_truthy(request.GET.get('inherit_subjects')) and validated_data['parent'].has_permission(user, osf_permissions.WRITE):
            parent = validated_data['parent']
            node.subjects.add(parent.subjects.all())
            node.save()

        if license_details:
            try:
                node.set_node_license(
                    {
                        'id': license_details.get('id') if license_details.get('id') else 'NONE',
                        'year': license_details.get('year'),
                        'copyrightHolders': license_details.get('copyrightHolders') or license_details.get('copyright_holders', []),
                    },
                    auth=get_user_auth(request),
                    save=True,
                )
            except ValidationError as e:
                raise InvalidModelValueError(detail=str(e.message))

        if not region_id:
            region_id = self.context.get('region_id')
        if region_id:
            node_settings = node.get_addon('osfstorage')
            node_settings.region_id = region_id
            node_settings.save()

        return node

    def update(self, node, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        assert isinstance(node, AbstractNode), 'node must be a Node'
        user = self.context['request'].user
        auth = get_user_auth(self.context['request'])

        if validated_data:
            if 'custom_citation' in validated_data:
                node.update_custom_citation(validated_data.pop('custom_citation'), auth)
            if 'tags' in validated_data:
                new_tags = set(validated_data.pop('tags', []))
                node.update_tags(new_tags, auth=auth)
            if 'region' in validated_data:
                validated_data.pop('region')
            if 'license_type' in validated_data or 'license' in validated_data:
                license_details = get_license_details(node, validated_data)
                validated_data['node_license'] = license_details
            if 'affiliated_institutions' in validated_data:
                institutions_list = validated_data.pop('affiliated_institutions')
                new_institutions = [{'_id': institution} for institution in institutions_list]

                update_institutions(node, new_institutions, user)
                node.save()
            if 'subjects' in validated_data:
                subjects = validated_data.pop('subjects', None)
                self.update_subjects(node, subjects, auth)

            try:
                node.update(validated_data, auth=auth)
            except ValidationError as e:
                raise InvalidModelValueError(detail=e.message)
            except PermissionsError:
                raise exceptions.PermissionDenied
            except NodeUpdateError as e:
                raise exceptions.ValidationError(detail=e.reason)
            except NodeStateError as e:
                raise InvalidModelValueError(detail=str(e))

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
    label = ser.CharField(required=False, allow_blank=True)
    url = ser.URLField(required=False, allow_blank=True)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        kwargs = self.context['request'].parser_context['kwargs']
        if 'provider' not in kwargs or (obj and obj.config.short_name != kwargs.get('provider')):
            kwargs.update({'provider': obj.config.short_name})

        return absolute_reverse(
            'nodes:node-addon-detail',
            kwargs=kwargs,
        )

    def create(self, validated_data):
        auth = Auth(self.context['request'].user)
        node = self.context['view'].get_node()
        addon = self.context['request'].parser_context['kwargs']['provider']

        return node.get_or_add_addon(addon, auth=auth)

class ForwardNodeAddonSettingsSerializer(NodeAddonSettingsSerializerBase):

    def update(self, instance, validated_data):
        request = self.context['request']
        user = request.user
        auth = Auth(user)
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

        try:
            instance.save(request=request)
        except ValidationError as e:
            raise exceptions.ValidationError(detail=str(e))

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
                'path': folder_path,
            }
        return set_folder, folder_info

    def get_account_or_error(self, addon_name, external_account_id, auth):
        external_account = ExternalAccount.load(external_account_id)
        if not external_account:
            raise exceptions.NotFound('Unable to find requested account.')
        if not auth.user.external_accounts.filter(id=external_account.id).exists():
            raise exceptions.PermissionDenied('Requested action requires account ownership.')
        if external_account.provider != addon_name:
            raise Conflict('Cannot authorize the {} addon with an account for {}'.format(addon_name, external_account.provider))
        return external_account

    def should_call_set_folder(self, folder_info, instance, auth, node_settings):
        if (folder_info and not (   # If we have folder information to set
                instance and getattr(instance, 'folder_id', False) and (  # and the settings aren't already configured with this folder
                    instance.folder_id == folder_info or (hasattr(folder_info, 'get') and instance.folder_id == folder_info.get('id', False))
                )
        )):
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
    forked_date = VersionedDateTimeField(read_only=True)

    def create(self, validated_data):
        node = validated_data.pop('node')
        fork_title = validated_data.pop('title', None)
        request = self.context['request']
        auth = get_user_auth(request)
        fork = node.fork_node(auth, title=fork_title)

        try:
            fork.save()
        except ValidationError as e:
            raise InvalidModelValueError(detail=e.message)

        return fork


class CompoundIDField(IDField):
    """ID field to use with another resource related to the node. CompoundIDField IDs have the form "<resource-id>-<related-id>"."""

    def __init__(self, *args, **kwargs):
        kwargs['source'] = kwargs.pop('source', '_id')
        kwargs['help_text'] = kwargs.get('help_text', 'Unique ID that is a compound of two objects. Has the form "<resource-id>-<related-id>". Example: "abc12-xyz34"')
        super(CompoundIDField, self).__init__(*args, **kwargs)

    def _get_resource_id(self):
        return self.context['request'].parser_context['kwargs']['node_id']

    # override IDField
    def get_id(self, obj):
        resource_id = self._get_resource_id()
        related_id = obj._id
        return '{}-{}'.format(resource_id, related_id)

    def to_representation(self, value):
        resource_id = self._get_resource_id()
        related_id = super(CompoundIDField, self).to_representation(value)
        return '{}-{}'.format(resource_id, related_id)


class NodeContributorsSerializer(JSONAPISerializer):
    """ Separate from UserSerializer due to necessity to override almost every field as read only
    """
    non_anonymized_fields = [
        'bibliographic',
        'permission',
    ]
    filterable_fields = frozenset([
        'id',
        'bibliographic',
        'permission',
        'index',
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    index = ser.IntegerField(required=False, read_only=True, source='_order')

    bibliographic = ser.BooleanField(
        help_text='Whether the user will be included in citations for this node or not.',
        default=True,
    )
    permission = ser.ChoiceField(
        choices=osf_permissions.API_CONTRIBUTOR_PERMISSIONS, required=False, allow_null=True,
        default=osf_permissions.WRITE,
        help_text='User permission level. Must be "read", "write", or "admin". Defaults to "write".',
    )
    unregistered_contributor = ser.SerializerMethodField()

    links = LinksField({
        'self': 'get_absolute_url',
    })

    users = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'},
        always_embed=True,
    )

    node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<node._id>'},
    )

    class Meta:
        type_ = 'contributors'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'nodes:node-contributor-detail',
            kwargs={
                'user_id': obj.user._id,
                'node_id': self.context['request'].parser_context['kwargs']['node_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def get_unregistered_contributor(self, obj):
        # SerializerMethodField works for both Node and Preprint contributors
        if hasattr(obj, 'preprint'):
            unclaimed_records = obj.user.unclaimed_records.get(obj.preprint._id, None)
        else:
            unclaimed_records = obj.user.unclaimed_records.get(obj.node._id, None)
        if unclaimed_records:
            return unclaimed_records.get('name', None)


class NodeContributorsCreateSerializer(NodeContributorsSerializer):
    """
    Overrides NodeContributorsSerializer to add email, full_name, send_email, and non-required index and users field.
    """

    id = IDField(source='_id', required=False, allow_null=True)
    full_name = ser.CharField(required=False)
    email = ser.EmailField(required=False, source='user.email', write_only=True)
    index = ser.IntegerField(required=False, source='_order')

    users = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'},
        always_embed=True,
        required=False,
    )

    email_preferences = ['default', 'false']

    def get_proposed_permissions(self, validated_data):
        return validated_data.get('permission') or osf_permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS

    def validate_data(self, node, user_id=None, full_name=None, email=None, index=None):
        if not user_id and not full_name:
            raise exceptions.ValidationError(detail='A user ID or full name must be provided to add a contributor.')
        if user_id and email:
            raise exceptions.ValidationError(detail='Do not provide an email when providing this user_id.')
        if index > len(node.contributors):
            raise exceptions.ValidationError(detail='{} is not a valid contributor index for node with id {}'.format(index, node._id))

    def create(self, validated_data):
        id = validated_data.get('_id')
        email = validated_data.get('user', {}).get('email', None)
        index = None
        if '_order' in validated_data:
            index = validated_data.pop('_order')
        node = self.context['resource']
        auth = Auth(self.context['request'].user)
        full_name = validated_data.get('full_name')
        bibliographic = validated_data.get('bibliographic')
        send_email = self.context['request'].GET.get('send_email') or self.context['default_email']
        permissions = self.get_proposed_permissions(validated_data)

        self.validate_data(node, user_id=id, full_name=full_name, email=email, index=index)

        if send_email not in self.email_preferences:
            raise exceptions.ValidationError(detail='{} is not a valid email preference.'.format(send_email))

        try:
            contributor_dict = {
                'auth': auth, 'user_id': id, 'email': email, 'full_name': full_name, 'send_email': send_email,
                'bibliographic': bibliographic, 'index': index, 'save': True,
            }

            contributor_dict['permissions'] = permissions
            contributor_obj = node.add_contributor_registered_or_not(**contributor_dict)
        except ValidationError as e:
            raise exceptions.ValidationError(detail=e.messages[0])
        except ValueError as e:
            raise exceptions.NotFound(detail=e.args[0])
        return contributor_obj


class NodeContributorDetailSerializer(NodeContributorsSerializer):
    """
    Overrides node contributor serializer to add additional methods
    """
    id = IDField(required=True, source='_id')
    index = ser.IntegerField(required=False, read_only=False, source='_order')

    def update(self, instance, validated_data):
        index = None
        if '_order' in validated_data:
            index = validated_data.pop('_order')

        auth = Auth(self.context['request'].user)
        node = self.context['resource']

        if 'bibliographic' in validated_data:
            bibliographic = validated_data.get('bibliographic')
        else:
            bibliographic = node.get_visible(instance.user)
        permission = validated_data.get('permission') or instance.permission
        try:
            if index is not None:
                node.move_contributor(instance.user, auth, index, save=True)
            node.update_contributor(instance.user, permission, bibliographic, auth, save=True)
        except node.state_error as e:
            raise exceptions.ValidationError(detail=str(e))
        except ValueError as e:
            raise exceptions.ValidationError(detail=str(e))
        instance.refresh_from_db()
        return instance


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
        related_view_kwargs={'node_id': '<child._id>'},
        always_embed=True,

    )
    class Meta:
        type_ = 'node_links'

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'nodes:node-pointer-detail',
            kwargs={
                'node_link_id': obj._id,
                'node_id': self.context['request'].parser_context['kwargs']['node_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        auth = Auth(user)
        node = self.context['view'].get_node()
        target_node_id = validated_data['_id']
        pointer_node = AbstractNode.load(target_node_id)
        if not pointer_node or pointer_node.is_collection:
            raise InvalidModelValueError(
                source={'pointer': '/data/relationships/node_links/data/id'},
                detail='Target Node \'{}\' not found.'.format(target_node_id),
            )
        try:
            pointer = node.add_pointer(pointer_node, auth, save=True)
            return pointer
        except ValueError as e:
            raise InvalidModelValueError(
                source={'pointer': '/data/relationships/node_links/data/id'},
                detail=str(e),
            )

    def update(self, instance, validated_data):
        pass


class NodeStorageProviderSerializer(JSONAPISerializer):
    id = ser.SerializerMethodField(read_only=True)
    kind = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True)
    path = ser.CharField(read_only=True)
    node = ser.CharField(source='node_id', read_only=True)
    provider = ser.CharField(read_only=True)
    files = NodeFileHyperLinkField(
        related_view='nodes:node-files',
        related_view_kwargs={'node_id': '<node._id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder',
        never_embed=True,
    )
    links = LinksField({
        'upload': WaterbutlerLink(),
        'new_folder': WaterbutlerLink(kind='folder'),
        'storage_addons': 'get_storage_addons_url',
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
                'provider': obj.provider,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def get_storage_addons_url(self, obj):
        return absolute_reverse(
            'addons:addon-list',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
            query_kwargs={
                'filter[categories]': 'storage',
            },
        )

class InstitutionRelated(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)
    class Meta:
        type_ = 'institutions'


class NodeInstitutionsRelationshipSerializer(BaseAPISerializer):
    data = ser.ListField(child=InstitutionRelated())
    links = LinksField({
        'self': 'get_self_url',
        'html': 'get_related_url',
    })

    def get_self_url(self, obj):
        return obj['self'].institutions_relationship_url

    def get_related_url(self, obj):
        return obj['self'].institutions_url

    class Meta:
        type_ = 'institutions'

    def make_instance_obj(self, obj):
        return {
            'data': obj.affiliated_institutions.all(),
            'self': obj,
        }

    def update(self, instance, validated_data):
        node = instance['self']
        user = self.context['request'].user
        update_institutions(node, validated_data['data'], user)
        node.save()

        return self.make_instance_obj(node)

    def create(self, validated_data):
        instance = self.context['view'].get_object()
        user = self.context['request'].user
        node = instance['self']
        update_institutions(node, validated_data['data'], user, post=True)
        node.save()

        return self.make_instance_obj(node)

class RegistrationSchemaRelationshipField(RelationshipField):

    def to_internal_value(self, registration_schema_id):
        schema = get_object_or_error(RegistrationSchema, registration_schema_id, self.context['request'])
        latest_version = RegistrationSchema.objects.get_latest_version(schema.name, only_active=False).schema_version
        if latest_version != schema.schema_version or not schema.active:
            raise exceptions.ValidationError('Registration supplement must be an active schema.')
        return {'registration_schema': schema}


class DraftRegistrationSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    registration_metadata = ser.DictField(required=False)
    datetime_initiated = VersionedDateTimeField(read_only=True)
    datetime_updated = VersionedDateTimeField(read_only=True)

    branched_from = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<branched_from._id>'},
    )

    initiator = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<initiator._id>'},
    )

    registration_schema = RegistrationSchemaRelationshipField(
        related_view='schemas:registration-schema-detail',
        related_view_kwargs={'schema_id': '<registration_schema._id>'},
        required=True,
        read_only=False,
    )

    provider = RegistrationProviderRelationshipField(
        related_view='providers:registration-providers:registration-provider-detail',
        related_view_kwargs={'provider_id': '<provider._id>'},
        read_only=False,
        required=False,
    )

    links = LinksField({
        'html': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return obj.absolute_url

    def create(self, validated_data):
        initiator = get_user_auth(self.context['request']).user
        node = self.context['view'].get_node()
        metadata = validated_data.pop('registration_metadata', None)
        schema = validated_data.pop('registration_schema')

        provider = validated_data.pop('provider', None) or RegistrationProvider.load('osf')
        # TODO: this
        # if not provider.schemas_acceptable.filter(id=schema.id).exists():
        #     raise exceptions.ValidationError('Invalid schema for provider.')

        draft = DraftRegistration.create_from_node(node=node, user=initiator, schema=schema, provider=provider)
        reviewer = is_prereg_admin_not_project_admin(self.context['request'], draft)

        if metadata:
            try:
                # Required fields are only required when creating the actual registration, not updating the draft.
                draft.validate_metadata(metadata=metadata, reviewer=reviewer, required_fields=False)
            except ValidationError as e:
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

    registration_schema = RelationshipField(
        related_view='schemas:registration-schema-detail',
        related_view_kwargs={'schema_id': '<registration_schema._id>'},
    )

    provider = RegistrationProviderRelationshipField(
        related_view='providers:registration-providers:registration-provider-detail',
        related_view_kwargs={'provider_id': '<provider._id>'},
        read_only=True,
    )

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
            except ValidationError as e:
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
        'date_created',
    ])

    key = ser.CharField(read_only=True)
    id = IDField(source='_id', read_only=True)
    date_created = VersionedDateTimeField(source='created', read_only=True)
    anonymous = ser.BooleanField(required=False, default=False)
    name = ser.CharField(required=False, default='Shared project link')

    links = LinksField({
        'self': 'get_absolute_url',
    })

    creator = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
    )

    nodes = RelationshipField(
        related_view='view-only-links:view-only-link-nodes',
        related_view_kwargs={'link_id': '<_id>'},
        self_view='view-only-links:view-only-link-nodes-relationships',
        self_view_kwargs={'link_id': '<_id>'},
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
                anonymous=anonymous,
            )
        except ValidationError:
            raise exceptions.ValidationError('Invalid link name.')

        return view_only_link

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'nodes:node-view-only-link-detail',
            kwargs={
                'link_id': obj._id,
                'node_id': self.context['request'].parser_context['kwargs']['node_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
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

        if 'name' in validated_data:
            link.name = validated_data.get('name')
        if 'anonymous' in validated_data:
            link.anonymous = validated_data.get('anonymous')

        link.save()
        return link


class NodeSettingsSerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    access_requests_enabled = ser.BooleanField()
    anyone_can_comment = ser.SerializerMethodField()
    anyone_can_edit_wiki = ser.SerializerMethodField()
    wiki_enabled = ser.SerializerMethodField()
    redirect_link_enabled = ser.SerializerMethodField()
    redirect_link_url = ser.SerializerMethodField()
    redirect_link_label = ser.SerializerMethodField()

    view_only_links = RelationshipField(
        related_view='nodes:node-view-only-links',
        related_view_kwargs={'node_id': '<_id>'},
    )

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_anyone_can_comment(self, obj):
        return obj.comment_level == 'public'

    def get_wiki_enabled(self, obj):
        return self.context['wiki_addon'] is not None

    def get_anyone_can_edit_wiki(self, obj):
        wiki_addon = self.context['wiki_addon']
        return wiki_addon.is_publicly_editable if wiki_addon else None

    def get_redirect_link_enabled(self, obj):
        return self.context['forward_addon'] is not None

    def get_redirect_link_url(self, obj):
        forward_addon = self.context['forward_addon']
        return forward_addon.url if forward_addon else None

    def get_redirect_link_label(self, obj):
        forward_addon = self.context['forward_addon']
        return forward_addon.label if forward_addon else None

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'nodes:node-settings',
            kwargs={
                'node_id': self.context['request'].parser_context['kwargs']['node_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    class Meta:
        type_ = 'node-settings'


class NodeSettingsUpdateSerializer(NodeSettingsSerializer):
    anyone_can_comment = ser.BooleanField(write_only=True, required=False)
    wiki_enabled = ser.BooleanField(write_only=True, required=False)
    anyone_can_edit_wiki = ser.BooleanField(write_only=True, required=False)
    redirect_link_enabled = ser.BooleanField(write_only=True, required=False)
    redirect_link_url = ser.URLField(write_only=True, required=False)
    redirect_link_label = ser.CharField(max_length=50, write_only=True, required=False)

    def to_representation(self, instance):
        """
        Overriding to_representation allows using different serializers for the request and response.
        """
        context = self.context
        context['wiki_addon'] = instance.get_addon('wiki')
        context['forward_addon'] = instance.get_addon('forward')
        return NodeSettingsSerializer(instance=instance, context=context).data

    def update(self, obj, validated_data):
        user = self.context['request'].user
        auth = get_user_auth(self.context['request'])
        admin_only_field_names = [
            'access_requests_enabled',
            'anyone_can_comment',
            'anyone_can_edit_wiki',
            'wiki_enabled',
        ]

        if set(validated_data.keys()).intersection(set(admin_only_field_names)) and not obj.has_permission(user, osf_permissions.ADMIN):
            raise exceptions.PermissionDenied

        self.update_node_fields(obj, validated_data, auth)
        self.update_wiki_fields(obj, validated_data, auth)
        self.update_forward_fields(obj, validated_data, auth)
        return obj

    def update_node_fields(self, obj, validated_data, auth):
        access_requests_enabled = validated_data.get('access_requests_enabled')
        anyone_can_comment = validated_data.get('anyone_can_comment')
        save_node = False

        if access_requests_enabled is not None:
            obj.set_access_requests_enabled(access_requests_enabled, auth=auth)
            save_node = True
        if anyone_can_comment is not None:
            obj.comment_level = 'public' if anyone_can_comment else 'private'
            save_node = True
        if save_node:
            obj.save()

    def update_wiki_fields(self, obj, validated_data, auth):
        wiki_enabled = validated_data.get('wiki_enabled')
        anyone_can_edit_wiki = validated_data.get('anyone_can_edit_wiki')
        wiki_addon = self.context['wiki_addon']

        if wiki_enabled is not None:
            wiki_addon = self.enable_or_disable_addon(obj, wiki_enabled, 'wiki', auth)

        if anyone_can_edit_wiki is not None:
            if not obj.is_public and anyone_can_edit_wiki:
                raise exceptions.ValidationError(detail='To allow all OSF users to edit the wiki, the project must be public.')
            if wiki_addon:
                try:
                    wiki_addon.set_editing(permissions=anyone_can_edit_wiki, auth=auth, log=True)
                except NodeStateError:
                    return
                wiki_addon.save()
            else:
                raise exceptions.ValidationError(detail='You must have the wiki enabled before changing wiki settings.')

    def update_forward_fields(self, obj, validated_data, auth):
        redirect_link_enabled = validated_data.get('redirect_link_enabled')
        redirect_link_url = validated_data.get('redirect_link_url')
        redirect_link_label = validated_data.get('redirect_link_label')

        save_forward = False
        forward_addon = self.context['forward_addon']

        if redirect_link_enabled is not None:
            if not redirect_link_url and redirect_link_enabled:
                raise exceptions.ValidationError(detail='You must include a redirect URL to enable a redirect.')
            forward_addon = self.enable_or_disable_addon(obj, redirect_link_enabled, 'forward', auth)

        if redirect_link_url is not None:
            if not forward_addon:
                raise exceptions.ValidationError(detail='You must first set redirect_link_enabled to True before specifying a redirect link URL.')
            forward_addon.url = redirect_link_url
            obj.add_log(
                action='forward_url_changed',
                params=dict(
                    node=obj._id,
                    project=obj.parent_id,
                    forward_url=redirect_link_url,
                ),
                auth=auth,
            )
            save_forward = True

        if redirect_link_label is not None:
            if not forward_addon:
                raise exceptions.ValidationError(detail='You must first set redirect_link_enabled to True before specifying a redirect link label.')
            forward_addon.label = redirect_link_label
            save_forward = True

        if save_forward:
            try:
                forward_addon.save(request=self.context['request'])
            except ValidationError as e:
                raise exceptions.ValidationError(detail=str(e))

    def enable_or_disable_addon(self, obj, should_enable, addon_name, auth):
        """
        Returns addon, if exists, otherwise returns None
        """
        addon = obj.get_or_add_addon(addon_name, auth=auth) if should_enable else obj.delete_addon(addon_name, auth)
        if type(addon) == bool:
            addon = None
        return addon


class NodeGroupsSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'name',
        'permission',
        'date_created',
    ])

    writeable_method_fields = frozenset([
        'permission',
    ])

    non_anonymized_fields = [
        'type',
        'permission',
    ]

    id = CompoundIDField(source='_id', read_only=True)
    type = TypeField()
    permission = ser.SerializerMethodField()
    name = ser.CharField(read_only=True)
    date_created = VersionedDateTimeField(source='created', read_only=True)
    date_modified = VersionedDateTimeField(source='modified', read_only=True)

    groups = RelationshipField(
        related_view='groups:group-detail',
        related_view_kwargs={'group_id': '<_id>'},
        required=False,
    )

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        node = self.context['node']
        return absolute_reverse(
            'nodes:node-group-detail', kwargs={
                'group_id': obj._id,
                'node_id': node._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def get_permission(self, obj):
        node = self.context['node']
        return obj.get_permission_to_node(node)

    class Meta:
        type_ = 'node-groups'


class NodeGroupsCreateSerializer(NodeGroupsSerializer):
    """
    Overrides NodeGroupSerializer so groups relationship is properly parsed
    (JSONAPIParser will flatten groups relationship into {'_id': 'group_id'},
    so _id field needs to be writeable so it's not dropped from validated_data)

    """
    id = IDField(source='_id', required=False, allow_null=True)

    groups = RelationshipField(
        related_view='groups:group-detail',
        related_view_kwargs={'group_id': '<_id>'},
        required=False,
    )

    def load_osf_group(self, _id):
        if not _id:
            raise exceptions.ValidationError(detail='Group relationship must be specified.')
        try:
            osf_group = OSFGroup.objects.get(_id=_id)
        except OSFGroup.DoesNotExist:
            raise exceptions.NotFound(detail='Group {} is invalid.'.format(_id))
        return osf_group

    def create(self, validated_data):
        auth = get_user_auth(self.context['request'])
        node = self.context['node']
        permission = validated_data.get('permission', osf_permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS)
        group = self.load_osf_group(validated_data.get('_id'))
        if group in node.osf_groups:
            raise exceptions.ValidationError(
                'The group {} has already been added to the node {}'.format(group._id, node._id),
            )

        try:
            node.add_osf_group(group, permission, auth)
        except PermissionsError as e:
            raise exceptions.PermissionDenied(detail=str(e))
        except ValueError as e:
            # permission is in writeable_method_fields, so validation happens on OSF Group model
            raise exceptions.ValidationError(detail=str(e.message))
        return group


class NodeGroupsDetailSerializer(NodeGroupsSerializer):
    """
    Overrides NodeGroupsSerializer to make id required.  Adds update method here.
    """
    id = CompoundIDField(source='_id', required=True)

    def update(self, obj, validated_data):
        auth = get_user_auth(self.context['request'])
        node = self.context['node']
        permission = validated_data.get('permission')
        if not permission:
            return obj
        try:
            node.update_osf_group(obj, permission, auth)
        except PermissionsError as e:
            raise exceptions.PermissionDenied(detail=str(e.message))
        except ValueError as e:
            # permission is in writeable_method_fields, so validation happens on OSF Group model
            raise exceptions.ValidationError(detail=str(e.message))
        return obj
