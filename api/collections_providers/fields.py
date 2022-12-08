from osf.models import CollectionProvider
from api.base.serializers import RelationshipField


class CollectionProviderRelationshipField(RelationshipField):
    def get_object(self, _id):
        return CollectionProvider.load(_id)

    def to_internal_value(self, data):
        provider = self.get_object(data)
        return {'provider': provider}
