import re

from rest_framework import serializers as ser

from api.base.utils import absolute_reverse

def _rapply(d, func, *args, **kwargs):
    """Apply a function to all values in a dictionary, recursively."""
    if isinstance(d, dict):
        return {
            key: _rapply(value, func, *args, **kwargs)
            for key, value in d.items()
        }
    else:
        return func(d, *args, **kwargs)

def _url_val(val, obj, **kwargs):
    """Function applied by `HyperlinksField` to get the correct value in the
    schema.
    """
    if isinstance(val, Link):  # If a Link is passed, get the url value
        return val.resolve_url(obj, **kwargs)
    elif isinstance(val, basestring):  # if a string is passed, it's an attribute
        return getattr(obj, val)
    else:
        return val

class LinksField(ser.Field):
    """Links field that resolves to a links object. Used in conjunction with `Link`.
    If the object to be serialized implements `get_absolute_url`, then the return value
    of that method is used for the `self` link.

    Example: ::

        links = LinksField({
            'html': 'absolute_url',
            'children': {
                'related': Link('nodes:node-children', pk='<pk>')
            },
            'contributors': {
                'related': Link('nodes:node-contributors', pk='<pk>')
            },
            'registrations': {
                'related': Link('nodes:node-registrations', pk='<pk>')
            },
        })
    """

    def __init__(self, links, *args, **kwargs):
        ser.Field.__init__(self, read_only=True, *args, **kwargs)
        self.links = links

    def get_attribute(self, obj):
        # We pass the object instance onto `to_representation`,
        # not just the field attribute.
        return obj

    def to_representation(self, obj):
        ret = _rapply(self.links, _url_val, obj=obj)
        if hasattr(obj, 'get_absolute_url'):
            ret['self'] = obj.get_absolute_url()
        return ret

_tpl_pattern = re.compile(r'\s*<\s*(\S*)\s*>\s*')
def _tpl(val):
    """Return value within ``< >`` if possible, else return ``None``."""
    match = _tpl_pattern.match(val)
    if match:
        return match.groups()[0]
    return None


class Link(object):
    """Link object to use in conjunction with Links field. Does reverse lookup of
    URLs given an endpoint name and attributed enclosed in `<>`.
    """

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint
        self.params = kwargs

    def resolve_url(self, obj):
        param_values = {}
        for name, attr_tpl in self.params.items():
            attr_name = _tpl(str(attr_tpl))
            if attr_name:
                attribute_value = getattr(obj, attr_name, ser.empty)
                if attribute_value is not ser.empty:
                    param_values[name] = attribute_value
                else:
                    raise AttributeError(
                        '{attr_name!r} is not a valid '
                        'attribute of {obj!r}'.format(
                            attr_name=attr_name, obj=obj,
                        ))
            else:
                param_values[name] = attr_tpl
        return absolute_reverse(self.endpoint, kwargs=param_values)


class JSONAPIListSerializer(ser.ListSerializer):

    def to_representation(self, data):
        # Don't envelope when serializing collection
        return [
            self.child.to_representation(item, envelope=None) for item in data
        ]

class JSONAPISerializer(ser.Serializer):
    """Base serializer. Requires that a `type_` option is set on `class Meta`. Also
    allows for enveloping of both single resources and collections.
    """

    # overrides Serializer
    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls()
        return JSONAPIListSerializer(*args, **kwargs)

    # overrides Serializer
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
        return ret
