from api.base.serializers import (
    LinksField,
    RelationshipField,
)
from api.base.utils import absolute_reverse
from api.nodes.serializers import NodeSerializer
from api.registrations.serializers import RegistrationSerializer


# Todo: Return relationships as relationships
class SparseNodeSerializer(NodeSerializer):
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
    ])
    links = LinksField({
        'self': 'get_absolute_url',  # self links will break ember data unless we make a specific sparse detail serializer
        'html': 'get_absolute_html_url',
    })
    detail = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<_id>'},
    )
    children = RelationshipField(
        related_view='sparse:node-children',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_node_count'},
    )
    parent = RelationshipField(
        related_view='sparse:node-detail',
        related_view_kwargs={'node_id': '<parent_id>'},
        filter_key='parent_node',
    )
    root = RelationshipField(
        related_view='sparse:node-detail',
        related_view_kwargs={'node_id': '<root._id>'},
    )

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'sparse:node-detail',
            kwargs={
                'node_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    # Overrides SparseFieldsetMixin
    def parse_sparse_fields(self, allow_unsafe=False, **kwargs):
        """
        SparseNodes are faster mostly because they subset the fields that they return
        to only the necessary fields for a list view.
        """
        fieldset = [
            'bibliographic_contributors',
            'category',
            'children',
            'contributors',
            'current_user_is_contributor',
            'current_user_is_contributor_or_group_member',
            'current_user_permissions',
            'date_created',
            'date_modified',
            'description',
            'detail',
            'fork',
            'is_public',
            'parent',
            'public',
            'root',
            'tags',
            'title',
        ]
        for field_name in self.fields.fields.copy().keys():
            if field_name in ('id', 'links', 'type'):
                # MUST return these fields
                continue
            if field_name not in fieldset:
                self.fields.pop(field_name)
        return super(SparseNodeSerializer, self).parse_sparse_fields(allow_unsafe, **kwargs)

    class Meta:
        type_ = 'sparse-nodes'


class SparseRegistrationSerializer(RegistrationSerializer):
    filterable_fields = frozenset([
        'category',
        'contributors',
        'date_created',
        'date_modified',
        'description',
        'detail',
        'id',
        'parent',
        'public',
        'root',
        'tags',
        'title',
    ])

    links = LinksField({
        'self': 'get_absolute_url',  # self links will break ember data unless we make a specific sparse detail serializer
        'html': 'get_absolute_html_url',
    })
    detail = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<_id>'},
    )
    children = RelationshipField(
        related_view='sparse:registration-children',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_node_count'},
    )
    parent = RelationshipField(
        related_view='sparse:registration-detail',
        related_view_kwargs={'node_id': '<parent_id>'},
        filter_key='parent_node',
    )
    root = RelationshipField(
        related_view='sparse:registration-detail',
        related_view_kwargs={'node_id': '<root._id>'},
    )

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'sparse:registration-detail',
            kwargs={
                'node_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    # Overrides SparseFieldsetMixin
    def parse_sparse_fields(self, allow_unsafe=False, **kwargs):
        """
        SparseRegistrations are faster mostly because they subset the fields that they return
        to only the necessary fields for a list view.
        """
        fieldset = [
            'archiving',
            'category',
            'children',
            'contributors',
            'current_user_is_contributor',
            'current_user_is_contributor_or_group_member',
            'current_user_permissions',
            'date_created',
            'date_modified',
            'description',
            'detail',
            'embargoed',
            'fork',
            'is_public',
            'parent',
            'pending_embargo_approval',
            'pending_embargo_termination_approval',
            'pending_registration_approval',
            'pending_withdrawal',
            'public',
            'registered_meta',
            'registration_schema',
            'root',
            'tags',
            'title',
            'withdrawn',

        ]
        for field_name in self.fields.fields.copy().keys():
            if field_name in ('id', 'links', 'type'):
                # MUST return these fields
                continue
            if field_name not in fieldset:
                self.fields.pop(field_name)
        return super(SparseRegistrationSerializer, self).parse_sparse_fields(allow_unsafe, **kwargs)

    class Meta:
        type_ = 'sparse-registrations'
