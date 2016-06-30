from website.models import Node, User
from website.files.models import FileNode

from api.base.serializers import (JSONAPISerializer, IDField, TypeField, RelationshipField)

def get_type(record):
    if isinstance(record, Node):
        return 'nodes'
    elif isinstance(record, User):
        return 'users'
    elif isinstance(record, FileNode):
        return 'files'

def get_related_view(record):
    kind = get_type(record)
    # slight hack, works for existing types
    singular = kind.rstrip('s')
    return '{}:{}-detail'.format(kind, singular)

def get_related_view_kwargs(guid):
    record = guid.referent
    kind = get_type(record)
    # slight hack, works for existing types
    singular = kind.rstrip('s')
    return {
        '{}_id'.format(singular): '<_id>'
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
            'type': 'get_type'
        }
    )

    def get_type(self, guid):
        return get_type(guid.referent)

    def get_absolute_url(self, obj):
        return obj.referent.get_absolute_url()
