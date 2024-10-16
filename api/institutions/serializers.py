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
    ShowIfObjectPermission,
)

from api.base.serializers import YearmonthField
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
    iri = ser.CharField(read_only=True, source='identifier_domain')
    ror_iri = ser.CharField(read_only=True, source='ror_uri')
    iris = ser.SerializerMethodField(read_only=True)
    assets = ser.SerializerMethodField(read_only=True)
    link_to_external_reports_archive = ShowIfObjectPermission(
        ser.CharField(read_only=True),
        permission='view_institutional_metrics',
    )
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

    department_metrics = ShowIfObjectPermission(
        RelationshipField(
            related_view='institutions:institution-department-metrics',
            related_view_kwargs={'institution_id': '<_id>'},
        ),
        permission='view_institutional_metrics',
    )

    user_metrics = ShowIfObjectPermission(
        RelationshipField(
            related_view='institutions:institution-user-metrics',
            related_view_kwargs={'institution_id': '<_id>'},
        ),
        permission='view_institutional_metrics',
    )

    summary_metrics = ShowIfObjectPermission(
        RelationshipField(
            related_view='institutions:institution-summary-metrics',
            related_view_kwargs={'institution_id': '<_id>'},
        ),
        permission='view_institutional_metrics',
    )

    def get_api_url(self, obj):
        return obj.absolute_api_v2_url

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def get_iris(self, obj):
        return list(obj.get_semantic_iris())

    def get_assets(self, obj):
        return {
            'logo': obj.logo_path,
            'logo_rounded': obj.logo_path_rounded_corners,
            'banner': obj.banner_path,
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
                node.add_affiliated_institution(inst, user)
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
                registration.add_affiliated_institution(inst, user)
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
        return f'{resource_id}-{related_id}'


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


class OldInstitutionUserMetricsSerializer(JSONAPISerializer):
    '''serializer for institution-users metrics

    used only when the INSTITUTIONAL_DASHBOARD_2024 feature flag is NOT active
    (and should be removed when that flag is permanently active)
    '''

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


class NewInstitutionUserMetricsSerializer(JSONAPISerializer):
    '''serializer for institution-users metrics

    used only when the INSTITUTIONAL_DASHBOARD_2024 feature flag is active
    (and should be renamed without "New" when that flag is permanently active)
    '''

    class Meta:
        type_ = 'institution-users'

    filterable_fields = frozenset({
        'department',
        'orcid_id',
    })

    id = IDField(source='meta.id', read_only=True)
    user_name = ser.CharField(read_only=True)
    department = ser.CharField(read_only=True, source='department_name')
    orcid_id = ser.CharField(read_only=True)
    month_last_login = YearmonthField(read_only=True)
    month_last_active = YearmonthField(read_only=True)
    account_creation_date = YearmonthField(read_only=True)

    public_projects = ser.IntegerField(read_only=True, source='public_project_count')
    private_projects = ser.IntegerField(read_only=True, source='private_project_count')
    public_registration_count = ser.IntegerField(read_only=True)
    embargoed_registration_count = ser.IntegerField(read_only=True)
    published_preprint_count = ser.IntegerField(read_only=True)
    public_file_count = ser.IntegerField(read_only=True)
    storage_byte_count = ser.IntegerField(read_only=True)

    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user_id>'},
    )
    institution = RelationshipField(
        related_view='institutions:institution-detail',
        related_view_kwargs={'institution_id': '<institution_id>'},
    )

    links = LinksField({})

    def get_absolute_url(self):
        return None  # there is no detail view for institution-users


class NewInstitutionSummaryMetricsSerializer(JSONAPISerializer):
    '''serializer for institution-summary metrics

    used only when the INSTITUTIONAL_DASHBOARD_2024 feature flag is active
    (and should be renamed without "New" when that flag is permanently active)
    '''

    class Meta:
        type_ = 'institution-summary-metrics'

    id = IDField(read_only=True)

    user_count = ser.IntegerField(read_only=True)
    public_project_count = ser.IntegerField(read_only=True)
    private_project_count = ser.IntegerField(read_only=True)
    public_registration_count = ser.IntegerField(read_only=True)
    embargoed_registration_count = ser.IntegerField(read_only=True)
    published_preprint_count = ser.IntegerField(read_only=True)
    public_file_count = ser.IntegerField(read_only=True)
    storage_byte_count = ser.IntegerField(read_only=True)
    monthly_logged_in_user_count = ser.IntegerField(read_only=True)
    monthly_active_user_count = ser.IntegerField(read_only=True)

    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user_id>'},
    )
    institution = RelationshipField(
        related_view='institutions:institution-detail',
        related_view_kwargs={'institution_id': '<institution_id>'},
    )

    links = LinksField({})

    def get_absolute_url(self):
        return None  # there is no detail view for institution-users


class InstitutionRelated(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)
    class Meta:
        type_ = 'institutions'
