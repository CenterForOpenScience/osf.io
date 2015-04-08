from rest_framework import serializers as ser


class JSONAPIListSerializer(ser.ListSerializer):

    def to_representation(self, data):
        # Don't envelope when serializing collection
        return [
            self.child.to_representation(item, envelope=None) for item in data
        ]


class JSONAPISerializer(ser.Serializer):
    """Base serializer that automatically attaches a links object. If the object to be
    serialized implements `get_absolute_url`, that is used in `links.self` in the final
    output. Additional links may optionally be added by implementing `get_links`.
    """

    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls()
        return JSONAPIListSerializer(*args, **kwargs)

    def get_links(self, obj):
        """Additional links to attach to the links object."""
        return {}

    def to_representation(self, obj, envelope='data'):
        """Serialize to final representation.

        :param obj: Object to be serialized.
        :param envelope: Key for resource object.
        """
        ret = {}
        meta = getattr(self, 'Meta', None)
        type_ = getattr(meta, 'type_', None)
        assert type_ is not None, 'Must define Meta.type_'
        data = super(JSONAPISerializer, self).to_representation(obj)
        data['type'] = type_
        if envelope:
            ret[envelope] = data
        else:
            ret = data
        ret['links'] = {}
        if hasattr(obj, 'get_absolute_url'):
            ret['links']['self'] = obj.get_absolute_url()
        links = self.get_links(obj)
        ret['links'].update(links)
        return ret
