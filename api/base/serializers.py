from rest_framework import serializers as ser

class LinkedSerializer(ser.Serializer):
    """Base serializer that automatically attaches a links object. If the object to be
    serialized implements `get_absolute_url`, that is used in `links.self` in the final
    output. Additional links may optionally be added by implementing `get_links`.
    """

    def get_links(self, obj):
        return {}

    def to_representation(self, obj):
        ret = super(LinkedSerializer, self).to_representation(obj)
        ret['links'] = {}

        if hasattr(obj, 'get_absolute_url'):
            ret['links']['self'] = obj.get_absolute_url()
        links = self.get_links(obj)
        ret['links'].update(links)
        return ret
