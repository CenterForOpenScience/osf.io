from api.base.serializers import (
    JSONAPISerializer
)


class SearchSerializer(JSONAPISerializer):

    def get_absolute_url(self, obj):
        pass

    class Meta:
        type_ = 'search'

