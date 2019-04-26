from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer,
    RelationshipField,
    RestrictedDictSerializer,
    LinksField,
    is_anonymized,
    VersionedDateTimeField,
    HideIfNotNodePointerLog,
    HideIfNotRegistrationPointerLog,
)

from osf.models import OSFUser, AbstractNode, Preprint
from osf.utils.names import impute_names_model
from osf.utils import permissions as osf_permissions


class NodeLogIdentifiersSerializer(RestrictedDictSerializer):

    doi = ser.CharField(read_only=True)
    ark = ser.CharField(read_only=True)

class NodeLogInstitutionSerializer(RestrictedDictSerializer):

    id = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True)

class NodeLogFileParamsSerializer(RestrictedDictSerializer):

    materialized = ser.CharField(read_only=True)
    url = ser.URLField(read_only=True)
    addon = ser.CharField(read_only=True)
    node_url = ser.URLField(read_only=True, source='node.url')
    node_title = ser.SerializerMethodField()

    def get_node_title(self, obj):
        user = self.context['request'].user
        node_title = obj['node']['title']
        node = AbstractNode.load(obj['node']['_id']) or Preprint.load(obj['node']['_id'])
        if not user.is_authenticated:
            if node.is_public:
                return node_title
        elif node.has_permission(user, osf_permissions.READ):
            return node_title
        return 'Private Component'

class NodeLogParamsSerializer(RestrictedDictSerializer):

    addon = ser.CharField(read_only=True)
    bucket = ser.CharField(read_only=True)
    contributors = ser.SerializerMethodField(read_only=True)
    data_set = ser.CharField(read_only=True, source='dataset')
    destination = NodeLogFileParamsSerializer(read_only=True)
    figshare_title = ser.CharField(read_only=True, source='figshare.title')
    forward_url = ser.CharField(read_only=True)
    github_user = ser.CharField(read_only=True, source='github.user')
    github_repo = ser.CharField(read_only=True, source='github.repo')
    bitbucket_user = ser.CharField(read_only=True, source='bitbucket.user')
    bitbucket_repo = ser.CharField(read_only=True, source='bitbucket.repo')
    gitlab_user = ser.CharField(read_only=True, source='gitlab.user')
    gitlab_repo = ser.CharField(read_only=True, source='gitlab.repo')
    file = ser.DictField(read_only=True)
    filename = ser.CharField(read_only=True)
    kind = ser.CharField(read_only=True)
    folder = ser.CharField(read_only=True)
    folder_name = ser.CharField(read_only=True)
    library_name = ser.CharField(read_only=True)
    license = ser.CharField(read_only=True, source='new_license')
    identifiers = NodeLogIdentifiersSerializer(read_only=True)
    institution = NodeLogInstitutionSerializer(read_only=True)
    old_page = ser.CharField(read_only=True)
    page = ser.CharField(read_only=True)
    page_id = ser.CharField(read_only=True)
    params_node = ser.SerializerMethodField(read_only=True)
    params_project = ser.SerializerMethodField(read_only=True)
    path = ser.CharField(read_only=True)
    pointer = ser.SerializerMethodField(read_only=True)
    preprint = ser.CharField(read_only=True)
    preprint_provider = ser.SerializerMethodField(read_only=True)
    previous_institution = NodeLogInstitutionSerializer(read_only=True)
    source = NodeLogFileParamsSerializer(read_only=True)
    study = ser.CharField(read_only=True)
    tag = ser.CharField(read_only=True)
    tags = ser.CharField(read_only=True)
    target = NodeLogFileParamsSerializer(read_only=True)
    template_node = ser.DictField(read_only=True)
    title_new = ser.CharField(read_only=True)
    title_original = ser.CharField(read_only=True)
    updated_fields = ser.DictField(read_only=True)
    urls = ser.DictField(read_only=True)
    version = ser.CharField(read_only=True)
    wiki = ser.DictField(read_only=True)
    citation_name = ser.CharField(read_only=True, source='citation.name')
    institution = NodeLogInstitutionSerializer(read_only=True)
    anonymous_link = ser.BooleanField(read_only=True)

    def get_view_url(self, obj):
        urls = obj.get('urls', None)
        if urls:
            view = urls.get('view', None)
            if view:
                return view
        return None

    def get_params_node(self, obj):
        node_id = obj.get('node', None)
        if node_id:
            node = AbstractNode.objects.filter(guids___id=node_id).values('title').get()
            return {'id': node_id, 'title': node['title']}
        return None

    def get_params_project(self, obj):
        project_id = obj.get('project', None)
        if project_id:
            node = AbstractNode.objects.filter(guids___id=project_id).values('title').get()
            return {'id': project_id, 'title': node['title']}
        return None

    def get_pointer(self, obj):
        user = self.context['request'].user
        pointer = obj.get('pointer', None)
        if pointer:
            pointer_node = AbstractNode.objects.get(guids___id=pointer['id'], guids___id__isnull=False)
            if not pointer_node.is_deleted:
                if pointer_node.is_public or (user.is_authenticated and pointer_node.has_permission(user, osf_permissions.READ)):
                    pointer['title'] = pointer_node.title
                    return pointer
        return None

    def get_contributors(self, obj):

        contributor_info = []

        if is_anonymized(self.context['request']):
            return contributor_info

        contributor_data = obj.get('contributors', None)
        params_node = obj.get('node', None)

        if contributor_data:
            contributor_ids = [each for each in contributor_data if isinstance(each, str)]
            # Very old logs may contain contributror data with dictionaries for non-registered contributors,
            # e.g. {'nr_email': 'foo@bar.com', 'nr_name': 'Foo Bar'}
            non_registered_contributor_data = [each for each in contributor_data if isinstance(each, dict)]

            users = (
                OSFUser.objects.filter(guids___id__in=contributor_ids)
                .only(
                    'fullname', 'given_name',
                    'middle_names', 'family_name',
                    'unclaimed_records', 'is_active',
                )
                .order_by('fullname')
            )
            for user in users:
                unregistered_name = None
                if user.unclaimed_records.get(params_node):
                    unregistered_name = user.unclaimed_records[params_node].get('name', None)

                contributor_info.append({
                    'id': user._id,
                    'full_name': user.fullname,
                    'given_name': user.given_name,
                    'middle_names': user.middle_names,
                    'family_name': user.family_name,
                    'unregistered_name': unregistered_name,
                    'active': user.is_active,
                })

            # Add unregistered contributor data
            for nr_contrib in non_registered_contributor_data:
                full_name = nr_contrib.get('nr_name', '')
                guessed_names = impute_names_model(full_name)
                contributor_info.append({
                    'id': None,
                    'full_name': full_name,
                    'unregistered_name': full_name,
                    'given_name': guessed_names['given_name'],
                    'middle_names': guessed_names['middle_names'],
                    'family_name': guessed_names['family_name'],
                    'active': False,
                })

        return contributor_info

    def get_preprint_provider(self, obj):
        preprint_id = obj.get('preprint', None)
        if preprint_id:
            preprint = Preprint.load(preprint_id)
            if preprint:
                provider = preprint.provider
                return {'url': provider.external_url, 'name': provider.name}
        return None

class NodeLogSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['action', 'date'])
    non_anonymized_fields = [
        'id',
        'date',
        'action',
    ]

    id = ser.CharField(read_only=True, source='_id')
    date = VersionedDateTimeField(read_only=True)
    action = ser.CharField(read_only=True)
    params = ser.SerializerMethodField(read_only=True)
    links = LinksField({'self': 'get_absolute_url'})

    class Meta:
        type_ = 'logs'

    node = RelationshipField(
        related_view=lambda n: 'registrations:registration-detail' if getattr(n, 'is_registration', False) else 'nodes:node-detail',
        related_view_kwargs={'node_id': '<node._id>'},
    )

    original_node = RelationshipField(
        related_view=lambda n: 'registrations:registration-detail' if getattr(n, 'is_registration', False) else 'nodes:node-detail',
        related_view_kwargs={'node_id': '<original_node._id>'},
    )

    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'},
    )

    # This would be a node_link, except that data isn't stored in the node log params
    linked_node = HideIfNotNodePointerLog(
        RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<params.pointer.id>'},
        ),
    )

    linked_registration = HideIfNotRegistrationPointerLog(
        RelationshipField(
            related_view='registrations:registration-detail',
            related_view_kwargs={'node_id': '<params.pointer.id>'},
        ),
    )

    template_node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<params.template_node.id>'},
    )

    def get_absolute_url(self, obj):
        return obj.absolute_url

    def get_params(self, obj):
        if obj.action == 'osf_storage_folder_created' and obj.params.get('urls'):
            obj.params.pop('urls')
        return NodeLogParamsSerializer(obj.params, context=self.context, read_only=True).data
