from rest_framework import serializers as ser
from rest_framework import exceptions

from osf.models import Node, Registration
from osf.utils import permissions as osf_permissions

from api.base.serializers import (
    JSONAPISerializer,
    RelationshipField,
    LinksField,
    JSONAPIRelationshipSerializer,
    BaseAPISerializer,
    ShowIfVersion,
    IDField,
)

from api.nodes.serializers import CompoundIDField
from api.base.exceptions import RelationshipPostMakesNoChanges
from api.base.utils import absolute_reverse


class InstitutionSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'id',
        'name',
        'auth_url',
    ])

    name = ser.CharField(read_only=True)
    id = ser.CharField(read_only=True, source='_id')
    description = ser.CharField(read_only=True)
    auth_url = ser.CharField(read_only=True)
    assets = ser.SerializerMethodField(read_only=True)
    links = LinksField({
        'self': 'get_api_url',
        'html': 'get_absolute_html_url',
    })

    nodes = RelationshipField(
        related_view='institutions:institution-nodes',
        related_view_kwargs={'institution_id': '<_id>'},
    )

    registrations = RelationshipField(
        related_view='institutions:institution-registrations',
        related_view_kwargs={'institution_id': '<_id>'},
    )

    users = RelationshipField(
        related_view='institutions:institution-users',
        related_view_kwargs={'institution_id': '<_id>'},
    )

    department_metrics = RelationshipField(
        related_view='institutions:institution-department-metrics',
        related_view_kwargs={'institution_id': '<_id>'},
    )

    user_metrics = RelationshipField(
        related_view='institutions:institution-user-metrics',
        related_view_kwargs={'institution_id': '<_id>'},
    )

    summary_metrics = RelationshipField(
        related_view='institutions:institution-summary-metrics',
        related_view_kwargs={'institution_id': '<_id>'},
    )

    def get_api_url(self, obj):
        return obj.absolute_api_v2_url

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def get_assets(self, obj):
        return {
            'logo': obj.logo_path,
            'logo_rounded': obj.logo_path_rounded_corners,
        }

    class Meta:
        type_ = 'institutions'

    # Deprecated fields
    logo_path = ShowIfVersion(
        ser.CharField(read_only=True, default=''),
        min_version='2.0', max_version='2.13',
    )

class NodeRelated(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)
    class Meta:
        type_ = 'nodes'

class InstitutionNodesRelationshipSerializer(BaseAPISerializer):
    data = ser.ListField(child=NodeRelated())
    links = LinksField({
        'self': 'get_self_url',
        'html': 'get_related_url',
    })

    def get_self_url(self, obj):
        return obj['self'].nodes_relationship_url

    def get_related_url(self, obj):
        return obj['self'].nodes_url

    class Meta:
        type_ = 'nodes'

    def create(self, validated_data):
        inst = self.context['view'].get_object()['self']
        user = self.context['request'].user
        node_dicts = validated_data['data']

        changes_flag = False
        for node_dict in node_dicts:
            node = Node.load(node_dict['_id'])
            if not node:
                raise exceptions.NotFound(detail='Node with id "{}" was not found'.format(node_dict['_id']))
            if not node.has_permission(user, osf_permissions.WRITE):
                raise exceptions.PermissionDenied(detail='Write permission on node {} required'.format(node_dict['_id']))
            if not node.is_affiliated_with_institution(inst):
                node.add_affiliated_institution(inst, user, save=True)
                changes_flag = True

        if not changes_flag:
            raise RelationshipPostMakesNoChanges

        return {
            'data': list(inst.nodes.filter(is_deleted=False, type='osf.node')),
            'self': inst,
        }

class RegistrationRelated(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)
    class Meta:
        type_ = 'registrations'

class InstitutionRegistrationsRelationshipSerializer(BaseAPISerializer):
    data = ser.ListField(child=RegistrationRelated())
    links = LinksField({
        'self': 'get_self_url',
        'html': 'get_related_url',
    })

    def get_self_url(self, obj):
        return obj['self'].registrations_relationship_url

    def get_related_url(self, obj):
        return obj['self'].registrations_url

    class Meta:
        type_ = 'registrations'

    def create(self, validated_data):
        inst = self.context['view'].get_object()['self']
        user = self.context['request'].user
        registration_dicts = validated_data['data']

        changes_flag = False
        for registration_dict in registration_dicts:
            registration = Registration.load(registration_dict['_id'])
            if not registration:
                raise exceptions.NotFound(detail='Registration with id "{}" was not found'.format(registration_dict['_id']))
            if not registration.has_permission(user, osf_permissions.WRITE):
                raise exceptions.PermissionDenied(detail='Write permission on registration {} required'.format(registration_dict['_id']))
            if not registration.is_affiliated_with_institution(inst):
                registration.add_affiliated_institution(inst, user, save=True)
                changes_flag = True

        if not changes_flag:
            raise RelationshipPostMakesNoChanges

        return {
            'data': list(inst.nodes.filter(is_deleted=False, type='osf.registration')),
            'self': inst,
        }


class InstitutionSummaryMetricSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'institution-summary-metrics'

    id = IDField(source='institution_id', read_only=True)
    public_project_count = ser.IntegerField(read_only=True)
    private_project_count = ser.IntegerField(read_only=True)
    user_count = ser.IntegerField(read_only=True)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'institutions:institution-summary-metrics',
            kwargs={
                'institution_id': self.context['request'].parser_context['kwargs']['institution_id'],
                'version': 'v2',
            },
        )


class UniqueDeptIDField(CompoundIDField):
    """Creates a unique department ID of the form "<institution-id>-<dept-id>"."""

    def __init__(self, *args, **kwargs):
        kwargs['source'] = kwargs.pop('source', 'name')
        kwargs['help_text'] = kwargs.get('help_text', 'Unique ID that is a compound of two objects. Has the form "<institution-id>-<dept-id>". Example: "cos-psych"')
        super().__init__(*args, **kwargs)

    def _get_resource_id(self):
        return self.context['request'].parser_context['kwargs']['institution_id']

    def to_representation(self, value):
        resource_id = self._get_resource_id()
        related_id = super(CompoundIDField, self).to_representation(value).replace(' ', '-')
        return '{}-{}'.format(resource_id, related_id)


class InstitutionDepartmentMetricsSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'institution-departments'

    id = UniqueDeptIDField(source='name', read_only=True)
    name = ser.CharField(read_only=True)
    number_of_users = ser.IntegerField(read_only=True)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    filterable_fields = frozenset([
        'id',
        'name',
        'number_of_users',
    ])

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'institutions:institution-department-metrics',
            kwargs={
                'institution_id': self.context['request'].parser_context['kwargs']['institution_id'],
                'version': 'v2',
            },
        )


class InstitutionUserMetricsSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'institution-users'

    id = IDField(source='user_id', read_only=True)
    user_name = ser.CharField(read_only=True)
    public_projects = ser.IntegerField(source='public_project_count', read_only=True)
    private_projects = ser.IntegerField(source='private_project_count', read_only=True)
    department = ser.CharField(read_only=True)

    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user_id>'},
    )

    links = LinksField({
        'self': 'get_absolute_url',
    })

    filterable_fields = frozenset([
        'id',
        'user_name',
        'public_projects',
        'private_projects',
        'department',
    ])

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'institutions:institution-user-metrics',
            kwargs={
                'institution_id': self.context['request'].parser_context['kwargs']['institution_id'],
                'version': 'v2',
            },
        )
