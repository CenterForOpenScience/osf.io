import re

from rest_framework.fields import SkipField
from rest_framework import serializers as ser

from website.util.sanitize import strip_html
from api.base.utils import absolute_reverse, waterbutler_url_for

from website.util import rapply as _rapply

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


class JSONAPIHyperlinkedIdentityField(ser.HyperlinkedIdentityField):
    """
    HyperlinkedIdentityField that returns a nested dict with url,
    optional meta information, and link_type.

    Example:

        children = JSONAPIHyperlinkedIdentityField(view_name='nodes:node-children', lookup_field='pk',
                                    link_type='related', lookup_url_kwarg='node_id', meta={'count': 'get_node_count'})

    """

    def __init__(self, view_name=None, **kwargs):
        kwargs['read_only'] = True
        kwargs['source'] = '*'
        self.meta = kwargs.pop('meta', None)
        self.link_type = kwargs.pop('link_type', 'url')
        super(ser.HyperlinkedIdentityField, self).__init__(view_name, **kwargs)

    # overrides HyperlinkedIdentityField
    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        Returns null if lookup value is None
        """

        if getattr(obj, self.lookup_field) is None:
            return None

        return super(ser.HyperlinkedIdentityField, self).get_url(obj, view_name, request, format)

    # overrides HyperlinkedIdentityField
    def to_representation(self, value):
        """
        Returns nested dictionary in format {'links': {'self.link_type': ... }

        If no meta information, self.link_type is equal to a string containing link's URL.  Otherwise,
        the link is represented as a links object with 'href' and 'meta' members.
        """
        url = super(JSONAPIHyperlinkedIdentityField, self).to_representation(value)

        if self.meta:
            meta = {}
            for key in self.meta:
                meta[key] = _rapply(self.meta[key], _url_val, obj=value, serializer=self.parent)
            self.meta = meta

            return {'links': {self.link_type: {'href': url, 'meta': self.meta}}}
        else:
            return {'links': {self.link_type: url}}


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
        attribute_value = getattr(obj, attr_name, ser.empty)
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
    URLs given an endpoint name and attributed enclosed in `<>`.
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


class JSONAPIListSerializer(ser.ListSerializer):

    def to_representation(self, data):
        # Don't envelope when serializing collection
        return [
            self.child.to_representation(item, envelope=None) for item in data
        ]


class JSONAPISerializer(ser.Serializer):
    """Base serializer. Requires that a `type_` option is set on `class Meta`. Also
    allows for enveloping of both single resources and collections.  Looks to nest fields
    according to JSON API spec. Relational fields must use JSONAPIHyperlinkedIdentityField.
    Self/html links must be nested under "links".
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

        data = collections.OrderedDict([('id', ''), ('type', type_), ('attributes', collections.OrderedDict()),
                                        ('relationships', collections.OrderedDict()), ('links', {})])

        fields = [field for field in self.fields.values() if not field.write_only]

        for field in fields:
            try:
                attribute = field.get_attribute(obj)
            except SkipField:
                continue

            if isinstance(field, JSONAPIHyperlinkedIdentityField):
                data['relationships'][field.field_name] = field.to_representation(attribute)
            elif field.field_name == 'id':
                data['id'] = field.to_representation(attribute)
            elif field.field_name == 'links':
                data['links'] = field.to_representation(attribute)
            else:
                if attribute is None:
                    # We skip `to_representation` for `None` values so that
                    # fields do not have to explicitly deal with that case.
                    data['attributes'][field.field_name] = None
                else:
                    data['attributes'][field.field_name] = field.to_representation(attribute)

        if not data['relationships']:
            del data['relationships']

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
