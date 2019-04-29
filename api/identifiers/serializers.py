from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.utils import absolute_reverse, get_user_auth
from api.base.exceptions import ServiceUnavailableError
from api.base.serializers import JSONAPISerializer, RelationshipField, IDField, LinksField
from osf.models import NodeLog
from framework.exceptions import HTTPError

from website.identifiers.utils import get_or_create_identifiers


class RegistrationIdentifierSerializer(JSONAPISerializer):
    writeable_method_fields = frozenset([
        'category',
    ])

    category = ser.SerializerMethodField()

    filterable_fields = frozenset(['category'])

    value = ser.CharField(read_only=True)

    referent = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<referent._id>'},
    )

    id = IDField(source='_id', read_only=True)

    links = LinksField({'self': 'self_url'})

    class Meta:
        type_ = 'identifiers'

    def get_category(self, obj):
        if obj.category == 'legacy_doi':
            return 'doi'
        return obj.category

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def get_id(self, obj):
        return obj._id

    def get_detail_url(self, obj):
        return '{}/identifiers/{}'.format(obj.absolute_api_v2_url, obj._id)

    def self_url(self, obj):
        return absolute_reverse(
            'identifiers:identifier-detail', kwargs={
                'identifier_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def create(self, validated_data):
        node = self.context['view'].get_node()
        auth = get_user_auth(self.context['request'])
        if validated_data.get('category', None) == 'doi':
            if node.get_identifier('doi'):
                raise exceptions.ValidationError('A DOI already exists for this resource.')
            try:
                identifiers = get_or_create_identifiers(node)
            except HTTPError:
                raise exceptions.ValidationError('Error response from client.')
            except TypeError:
                raise ServiceUnavailableError()
            for category, value in identifiers.items():
                node.set_identifier_value(category, value)
            node.add_log(
                NodeLog.EXTERNAL_IDS_ADDED,
                params={
                    'parent_node': node.parent_id,
                    'node': node._id,
                    'identifiers': identifiers,
                },
                auth=auth,
            )
            return node.identifiers.get(category='doi')
        else:
            raise exceptions.ValidationError('You can only mint a DOI, not a different type of identifier.')


class NodeIdentifierSerializer(RegistrationIdentifierSerializer):

    referent = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<referent._id>'},
    )


class PreprintIdentifierSerializer(RegistrationIdentifierSerializer):

    referent = RelationshipField(
        related_view='preprints:preprint-detail',
        related_view_kwargs={'preprint_id': '<referent._id>'},
    )
