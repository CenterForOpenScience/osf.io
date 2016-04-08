from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer,
    RelationshipField,
    RestrictedDictSerializer,
    LinksField,
)
from website.project.model import Node


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
    node_title = ser.URLField(read_only=True, source='node.title')


class NodeLogParamsSerializer(RestrictedDictSerializer):

    addon = ser.CharField(read_only=True)
    bucket = ser.CharField(read_only=True)
    data_set = ser.CharField(read_only=True, source='dataset')
    figshare_title = ser.CharField(read_only=True, source='figshare.title')
    forward_url = ser.CharField(read_only=True)
    github_user = ser.CharField(read_only=True, source='github.user')
    github_repo = ser.CharField(read_only=True, source='github.repo')
    filename = ser.CharField(read_only=True)
    kind = ser.CharField(read_only=True)
    folder = ser.CharField(read_only=True)
    folder_name = ser.CharField(read_only=True)
    identifiers = NodeLogIdentifiersSerializer(read_only=True)
    params_node = ser.SerializerMethodField(read_only=True)
    old_page = ser.CharField(read_only=True)
    page = ser.CharField(read_only=True)
    page_id = ser.CharField(read_only=True)
    path = ser.CharField(read_only=True)
    params_project = ser.SerializerMethodField(read_only=True)
    source = NodeLogFileParamsSerializer(read_only=True)
    destination = NodeLogFileParamsSerializer(read_only=True)
    view_url = ser.SerializerMethodField(read_only=True)
    study = ser.CharField(read_only=True)
    tag = ser.CharField(read_only=True)
    tags = ser.CharField(read_only=True)
    target = NodeLogFileParamsSerializer(read_only=True)
    title_new = ser.CharField(read_only=True)
    title_original = ser.CharField(read_only=True)
    updated_fields = ser.ListField(read_only=True)
    version = ser.CharField(read_only=True)
    citation_name = ser.CharField(read_only=True, source='citation.name')
    institution = NodeLogInstitutionSerializer(read_only=True)
    previous_institution = NodeLogInstitutionSerializer(read_only=True)

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
            node = Node.load(node_id)
            return {'id': node_id, 'title': node.title}
        return {}

    def get_params_project(self, obj):
        project_id = obj.get('project', None)
        if project_id:
            node = Node.load(project_id)
            return {'id': project_id, 'title': node.title}
        return {}

class NodeLogSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['action', 'date'])
    non_anonymized_fields = [
        'id',
        'date',
        'action',
    ]

    id = ser.CharField(read_only=True, source='_id')
    date = ser.DateTimeField(read_only=True)
    action = ser.CharField(read_only=True)
    params = NodeLogParamsSerializer(read_only=True)
    links = LinksField({'self': 'get_absolute_url'})

    class Meta:
        type_ = 'logs'

    nodes = RelationshipField(
        related_view='logs:log-nodes',
        related_view_kwargs={'log_id': '<pk>'},
    )
    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'},
    )

    contributors = RelationshipField(
        related_view='logs:log-contributors',
        related_view_kwargs={'log_id': '<pk>'},
    )

    # This would be a node_link, except that data isn't stored in the node log params
    linked_node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<params.pointer.id>'}
    )
    template_node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<params.template_node.id>'}
    )

    def get_absolute_url(self, obj):
        return obj.absolute_url
