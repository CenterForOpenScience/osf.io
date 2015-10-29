import re
import collections

from rest_framework.reverse import reverse
from rest_framework.fields import SkipField
from rest_framework import serializers as ser

from website import settings
from website.util.sanitize import strip_html
from website.util import waterbutler_api_url_for

from api.base import utils
from api.base.exceptions import InvalidQueryStringError, Conflict


class AllowMissing(ser.Field):

    def __init__(self, field, **kwargs):
        super(AllowMissing, self).__init__(**kwargs)
        self.field = field

    def to_representation(self, value):
        return self.field.to_representation(value)

    def bind(self, field_name, parent):
        super(AllowMissing, self).bind(field_name, parent)
        self.field.bind(field_name, self)

    def get_attribute(self, instance):
        """
        Overwrite the error message to return a blank value is if there is no existing value.
        This allows the display of keys that do not exist in the DB (gitHub on a new OSF account for example.)
        """
        try:
            return self.field.get_attribute(instance)
        except SkipField:
            return ''

    def to_internal_value(self, data):
        return self.field.to_internal_value(data)


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


class IDField(ser.CharField):
    def __init__(self, **kwargs):
        kwargs['label'] = 'ID'
        super(IDField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        update_methods = ['PUT', 'PATCH']
        if self.context['request'].method in update_methods:
            id_field = getattr(self.root.instance, self.source, '_id')
            if id_field != data:
                raise Conflict()
        return super(IDField, self).to_internal_value(data)


class TypeField(ser.CharField):

    def __init__(self, **kwargs):
        kwargs['write_only'] = True
        kwargs['required'] = True
        super(TypeField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        if self.root.Meta.type_ != data:
            raise Conflict()
        return super(TypeField, self).to_internal_value(data)


class TargetTypeField(ser.CharField):
    """
    Enforces that the related resource has the correct type
    """
    def __init__(self, **kwargs):
        kwargs['write_only'] = True
        kwargs['required'] = True
        self.target_type = kwargs.pop('target_type')
        super(TargetTypeField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        if self.target_type != data:
            raise Conflict()
        return super(TargetTypeField, self).to_internal_value(data)


class JSONAPIListField(ser.ListField):
    def to_internal_value(self, data):
        if not isinstance(data, list):
            self.fail('not_a_list', input_type=type(data).__name__)

        return super(JSONAPIListField, self).to_internal_value(data)


class JSONAPIHyperlinkedIdentityField(ser.HyperlinkedIdentityField):
    """
    HyperlinkedIdentityField that returns a nested dict with url,
    optional meta information, and link_type.

    Example:

        children = JSONAPIHyperlinkedIdentityField(view_name='nodes:node-children', lookup_field='pk',
                                    link_type='related', lookup_url_kwarg='node_id', meta={'count': 'get_node_count'})

    """

    def __init__(self, view_name=None, **kwargs):
        self.meta = kwargs.pop('meta', None)
        self.link_type = kwargs.pop('link_type', 'url')
        super(JSONAPIHyperlinkedIdentityField, self).__init__(view_name=view_name, **kwargs)

    # overrides HyperlinkedIdentityField
    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        Returns None if lookup value is None
        """

        if getattr(obj, self.lookup_field) is None:
            return None

        return super(JSONAPIHyperlinkedIdentityField, self).get_url(obj, view_name, request, format)

    # overrides HyperlinkedIdentityField
    def to_representation(self, value):
        """
        Returns nested dictionary in format {'links': {'self.link_type': ... }

        If no meta information, self.link_type is equal to a string containing link's URL.  Otherwise,
        the link is represented as a links object with 'href' and 'meta' members.
        """
        url = super(JSONAPIHyperlinkedIdentityField, self).to_representation(value)

        meta = {}
        for key in self.meta or {}:
            if key == 'count':
                show_related_counts = self.context['request'].query_params.get('related_counts', False)
                if utils.is_truthy(show_related_counts):
                    meta[key] = _rapply(self.meta[key], _url_val, obj=value, serializer=self.parent)
                elif utils.is_falsy(show_related_counts):
                    continue
                else:
                    raise InvalidQueryStringError(
                        detail="Acceptable values for the related_counts query param are 'true' or 'false'; got '{0}'".format(show_related_counts),
                        parameter='related_counts'
                    )
            else:
                meta[key] = _rapply(self.meta[key], _url_val, obj=value, serializer=self.parent)

        return {'links': {self.link_type: {'href': url, 'meta': meta}}}


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
        if hasattr(obj, 'get_absolute_url') and 'self' not in self.links:
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
        attribute_value = obj
        for attr_segment in attr_name.split('.'):
            attribute_value = getattr(attribute_value, attr_segment, ser.empty)
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
        return utils.absolute_reverse(
            self.endpoint,
            args=arg_values,
            kwargs=kwarg_values,
            query_kwargs=query_kwarg_values,
            **self.reverse_kwargs
        )


class WaterbutlerLink(Link):
    """Link object to use in conjunction with Links field. Builds a Waterbutler URL for files.
    """

    def __init__(self, must_be_file=None, must_be_folder=None, **kwargs):
        self.kwargs = kwargs
        self.must_be_file = must_be_file
        self.must_be_folder = must_be_folder

    def resolve_url(self, obj):
        """Reverse URL lookup for WaterButler routes
        """
        if self.must_be_folder is True and not obj.path.endswith('/'):
            return None
        if self.must_be_file is True and obj.path.endswith('/'):
            return None
        return waterbutler_api_url_for(obj.node._id, obj.provider, obj.path, **self.kwargs)


class NodeFileHyperLink(JSONAPIHyperlinkedIdentityField):
    def __init__(self, kind=None, kwargs=None, **kws):
        self.kind = kind
        self.kwargs = []
        for kw in (kwargs or []):
            if isinstance(kw, basestring):
                kw = (kw, kw)
            assert isinstance(kw, tuple) and len(kw) == 2
            self.kwargs.append(kw)
        super(NodeFileHyperLink, self).__init__(**kws)

    def get_url(self, obj, view_name, request, format):
        if self.kind and obj.kind != self.kind:
            return None
        return reverse(view_name, kwargs={attr_name: getattr(obj, attr) for (attr_name, attr) in self.kwargs}, request=request, format=format)


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
        """
        After validation, scrub HTML from validated_data prior to saving (for create and update views)

        Exclude 'type' and '_id' from validated_data.

        """
        ret = super(JSONAPISerializer, self).is_valid(**kwargs)

        if clean_html is True:
            self._validated_data = _rapply(self.validated_data, strip_html)

        self._validated_data.pop('type', None)
        self._validated_data.pop('target_type', None)

        update_methods = ['PUT', 'PATCH']
        if self.context['request'].method in update_methods:
            self._validated_data.pop('_id', None)

        return ret


def DevOnly(field):
    """Make a field only active in ``DEV_MODE``. ::

        experimental_field = DevMode(CharField(required=False))
    """
    return field if settings.DEV_MODE else None
