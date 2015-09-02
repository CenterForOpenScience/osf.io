import collections
import re

from rest_framework import serializers as ser
from website.util.sanitize import strip_html

from api.base.utils import absolute_reverse, waterbutler_url_for, deep_get
from api.base.filters import ForeignFieldReference


def _rapply(d, func, *args, **kwargs):
    """Apply a function to all values in a dictionary, recursively. Handles lists and dicts currently,
    as those are the only complex structures currently supported by DRF Serializer Fields."""
    if isinstance(d, collections.Mapping):
        return {
            key: _rapply(value, func, *args, **kwargs)
            for key, value in d.iteritems()
        }
    if isinstance(d, list):
        return [
            _rapply(item, func, *args, **kwargs) for item in d
        ]
    else:
        return func(d, *args, **kwargs)


def _url_val(val, obj, serializer, **kwargs):
    """Function applied by `HyperlinksField` to get the correct value in the
    schema.
    """
    if isinstance(val, Link):  # If a Link is passed, get the url value
        return val.resolve_url(obj, **kwargs)
    elif isinstance(val, basestring):  # if a string is passed, it's a method of the serializer
        return getattr(serializer, val)(obj)
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
                'related': Link('nodes:node-children', node_id='<pk>'),
                'count': 'get_node_count'
            },
            'contributors': {
                'related': Link('nodes:node-contributors', node_id='<pk>'),
                'count': 'get_contrib_count'
            },
            'registrations': {
                'related': Link('nodes:node-registrations', node_id='<pk>'),
                'count': 'get_registration_count'
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
        ret = _rapply(self.links, _url_val, obj=obj, serializer=self.parent)
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

def _get_attr_from_tpl(attr_tpl, obj):
    attr_name = _tpl(str(attr_tpl))
    if attr_name:
        attribute_value = deep_get(obj, attr_name)
        if attribute_value is not ser.empty:
            return attribute_value
        elif attr_name in obj:
            return obj[attr_name]
        else:
            raise AttributeError(
                '{attr_name!r} is not a valid '
                'attribute of {obj!r}'.format(
                    attr_name=attr_name, obj=obj,
                ))
    else:
        return attr_tpl


# TODO: Make this a Field that is usable on its own?
class Link(object):
    """Link object to use in conjunction with Links field. Does reverse lookup of
    URLs given an endpoint name and attributed enclosed in `<>`. This includes
    complex key strings like 'user.id'
    """

    def __init__(self, endpoint, args=None, kwargs=None, query_kwargs=None, **kw):
        self.endpoint = endpoint
        self.kwargs = kwargs or {}
        self.args = args or tuple()
        self.reverse_kwargs = kw
        self.query_kwargs = query_kwargs or {}

    def resolve_url(self, obj):
        kwarg_values = {key: _get_attr_from_tpl(attr_tpl, obj) for key, attr_tpl in self.kwargs.items()}
        arg_values = [_get_attr_from_tpl(attr_tpl, obj) for attr_tpl in self.args]
        query_kwarg_values = {key: _get_attr_from_tpl(attr_tpl, obj) for key, attr_tpl in self.query_kwargs.items()}
        # Presumably, if you have are expecting a value but the value is empty, then the link is invalid.
        for item in kwarg_values:
            if kwarg_values[item] is None:
                return None
        return absolute_reverse(
            self.endpoint,
            args=arg_values,
            kwargs=kwarg_values,
            query_kwargs=query_kwarg_values,
            **self.reverse_kwargs
        )


class WaterbutlerLink(Link):
    """Link object to use in conjunction with Links field. Builds a Waterbutler URL for files.
    """

    def __init__(self, args=None, kwargs=None, **kw):
        # self.endpoint = endpoint
        super(WaterbutlerLink, self).__init__(None, args, kwargs, None, **kw)

    def resolve_url(self, obj):
        """Reverse URL lookup for WaterButler routes
        """
        return waterbutler_url_for(obj['waterbutler_type'], obj['provider'], obj['path'], obj['node_id'], obj['cookie'], obj['args'])

class ForeignFieldMeta(ser.SerializerMetaclass):

    @classmethod
    def _get_foreign_fields(cls, attrs):
        return {
            name: field
            for name, field in attrs.iteritems()
            if getattr(field, '_foreign', False)
        }

    def __new__(cls, name, bases, attrs):
        attrs['_foreign_fields'] = cls._get_foreign_fields(attrs)
        return super(ForeignFieldMeta, cls).__new__(cls, name, bases, attrs)

class FieldTypeMixin(object):

    def get_field(self, key):
        if key in self._declared_fields:
            return self._declared_fields[key]
        elif key.split('.')[0] in self._foreign_fields:
            return self._foreign_fields[key.split('.')[0]]

    @classmethod
    def get_field_type(cls, key):
        key = key.strip()
        if key in cls._declared_fields:
            return type(cls._declared_fields[key])
        elif key.split('.')[0] in cls._foreign_fields:
            return ForeignFieldReference

class JSONAPIListSerializer(ser.ListSerializer, FieldTypeMixin):

    __metaclass__ = ForeignFieldMeta

    def to_representation(self, data):
        # Don't envelope when serializing collection
        return [
            self.child.to_representation(item, envelope=None) for item in data
        ]


class JSONAPISerializer(ser.Serializer, FieldTypeMixin):
    """Base serializer. Requires that a `type_` option is set on `class Meta`. Also
    allows for enveloping of both single resources and collections.
    """
    __metaclass__ = ForeignFieldMeta

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

    # overrides Serializer: Add HTML-sanitization similar to that used by APIv1 front-end views
    def is_valid(self, clean_html=True, **kwargs):
        """After validation, scrub HTML from validated_data prior to saving (for create and update views)"""
        ret = super(JSONAPISerializer, self).is_valid(**kwargs)

        if clean_html is True:
            self._validated_data = _rapply(self.validated_data, strip_html)
        return ret
