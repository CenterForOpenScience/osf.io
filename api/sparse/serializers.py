from api.base.serializers import (
    LinksField,
    RelationshipField,
)
from api.nodes.serializers import NodeSerializer
from api.registrations.serializers import RegistrationSerializer

# Todo: Return relationships as relationships
class SparseNodeSerializer(NodeSerializer):
    filterable_fields = frozenset([
        'title',
    ])

    links = LinksField({
        'self': None,  # self links will break ember data unless we make a specific sparse detail serializer
        'html': 'get_absolute_html_url',
    })

    detail = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<_id>'},
    )

    # Overrides SparseFieldsetMixin
    def parse_sparse_fields(self, allow_unsafe=False, **kwargs):
        """
        Since meeting submissions are actually nodes, we are subclassing the NodeSerializer,
        but we only want to return a subset of fields specific to meetings
        """
        fieldset = [
            'category',
            'contributors',
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
        'title',
    ])

    links = LinksField({
        'self': None,  # self links will break ember data unless we make a specific sparse detail serializer
        'html': 'get_absolute_html_url',
    })

    detail = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<_id>'},
    )

    # Overrides SparseFieldsetMixin
    def parse_sparse_fields(self, allow_unsafe=False, **kwargs):
        """
        Since meeting submissions are actually nodes, we are subclassing the NodeSerializer,
        but we only want to return a subset of fields specific to meetings
        """
        fieldset = [
            'category',
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
            'pending_embargo_termination_approval',
            'withdrawn',
            'pending_withdrawal',
            'pending_embargo_termination_approval',
            'embargoed',
            'pending_embargo_approval',
            'archiving',
            'registration_schema',
            'registered_meta',

        ]
        for field_name in self.fields.fields.copy().keys():
            if field_name in ('id', 'links', 'type'):
                # MUST return these fields
                continue
            if field_name not in fieldset:
                self.fields.pop(field_name)
        return super(SparseRegistrationSerializer, self).parse_sparse_fields(allow_unsafe, **kwargs)

    class Meta:
        type_ = 'sparse-nodes'
