from api.base.serializers import (
    JSONAPISerializer
)
from api.base.utils import absolute_reverse
from api.files.serializers import FileSerializer
from api.nodes.serializers import NodeSerializer
from api.registrations.serializers import RegistrationSerializer
from api.users.serializers import UserSerializer

from framework.auth.core import User

from website.files.models import FileNode
from website.models import Node


class SearchSerializer(JSONAPISerializer):

    def to_representation(self, data, envelope='data'):

        if isinstance(data, Node):
            if data.is_registration:
                serializer = RegistrationSerializer(data, context=self.context)
                return RegistrationSerializer.to_representation(serializer, data)
            serializer = NodeSerializer(data, context=self.context)
            return NodeSerializer.to_representation(serializer, data)

        if isinstance(data, User):
            serializer = UserSerializer(data, context=self.context)
            return UserSerializer.to_representation(serializer, data)

        if isinstance(data, FileNode):
            serializer = FileSerializer(data, context=self.context)
            return FileSerializer.to_representation(serializer, data)

        return None

    def get_absolute_url(self, obj):
        return absolute_reverse(
            view_name='search:search-search',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version']
            }
        )

    class Meta:
        type_ = 'search'
