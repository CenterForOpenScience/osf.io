from future.moves.urllib.parse import urljoin

from django.urls import resolve, reverse

from api.base.serializers import (JSONAPISerializer, IDField, TypeField, RelationshipField, LinksField)
from api.base.utils import absolute_reverse
from osf.models import OSFUser, AbstractNode, Registration, Guid, BaseFileNode
from website import settings as website_settings


def get_type(record):
    if isinstance(record, Registration):
        return 'registrations'
    elif isinstance(record, AbstractNode):
        return 'nodes'
    elif isinstance(record, OSFUser):
        return 'users'
    elif isinstance(record, BaseFileNode):
        return 'files'
    elif isinstance(record, Guid):
        return get_type(record.referent)

def get_related_view(record):
    kind = get_type(record)
    # slight hack, works for existing types
    singular = kind.rstrip('s')
    return '{}:{}-detail'.format(kind, singular)

def get_related_view_kwargs(record):
    kind = get_type(record)
    # slight hack, works for existing types
    singular = kind.rstrip('s')
    # The registration view_kwarg is node_id
    if singular == 'registration':
        singular = 'node'
    return {
        '{}_id'.format(singular): '<_id>',
    }

class GuidSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'guids'

    filterable_fields = tuple()

    id = IDField(source='_id', read_only=True)
    type = TypeField()

    referent = RelationshipField(
        related_view=get_related_view,
        related_view_kwargs=get_related_view_kwargs,
        related_meta={
            'type': 'get_type',
        },
    )
    links = LinksField({
        'self': 'get_absolute_url',
        'html': 'get_absolute_html_url',
    })

    def get_type(self, guid):
        return get_type(guid.referent)

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'guids:guid-detail', kwargs={
                'guids': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def get_absolute_html_url(self, obj):
        if not isinstance(obj.referent, BaseFileNode):
            return obj.referent.absolute_url
        return urljoin(website_settings.DOMAIN, '/{}/'.format(obj._id))

    def to_representation(self, obj):
        if self.context['view'].kwargs.get('is_embedded'):
            # Force the referent to serialize instead.
            obj = obj.referent
            ser = resolve(reverse(
                get_related_view(obj),
                kwargs={'node_id': obj._id, 'version': self.context['view'].kwargs.get('version', '2')},
            )).func.cls.serializer_class(context=self.context)
            [ser.context.update({k: v}) for k, v in self.context.items()]
            return ser.to_representation(obj)
        return super(GuidSerializer, self).to_representation(obj)
