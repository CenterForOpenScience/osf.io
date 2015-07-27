import collections
import re

from rest_framework import serializers as ser
from website.util.sanitize import strip_html
from website.models import Node
from api.base.utils import absolute_reverse, waterbutler_url_for
from rest_framework.exceptions import ValidationError
from framework.auth.core import Auth
from modularodm import Q


def _rapply(d, func, *args, **kwargs):
    """Apply a function to all values in a dictionary, recursively."""
    if isinstance(d, collections.Mapping):
        return {
            key: _rapply(value, func, *args, **kwargs)
            for key, value in d.iteritems()
        }
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


class LinksFieldWIthSelfLink(ser.Field):
    """Links field that resolves to a links object. Used in conjunction with `Link`.
    If the object to be serialized implements `get_absolute_url`, then the return value
    of that method is used for the `self` link.

    Example: ::

        links = LinksField({
            'html': 'absolute_url',
            'children': {
                'related': Link('nodes:node-children', pk='<pk>'),
                'count': 'get_node_count'
            },
            'contributors': {
                'related': Link('nodes:node-contributors', pk='<pk>'),
                'count': 'get_contrib_count'
            },
            'registrations': {
                'related': Link('nodes:node-registrations', pk='<pk>'),
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


class LinksField(LinksFieldWIthSelfLink):
    def to_representation(self, obj):
        ret = _rapply(self.links, _url_val, obj=obj, serializer=self.parent)
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

        attributes = super(JSONAPISerializer, self).to_representation(obj)
        top_level = {
            'id': attributes.get('id'),
            'links': attributes.get('links'),
            'relationships': attributes.get('relationships')
        }
        for i in top_level.keys():
            attributes.pop(i, None)
        data = collections.OrderedDict((
            ('id', top_level['id']),
            ('type', type_),
            ('attributes', attributes),
            ('links', top_level['links']),
            ('relationships', top_level['relationships'])))
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


class NodeIncludeSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(required=True)
    description = ser.CharField(required=False, allow_blank=True, allow_null=True)
    links = LinksFieldWIthSelfLink({'html': 'absolute_url'})

    def absolute_url(self, obj):
        return obj.absolute_url

    class Meta:
        type_ = 'nodes'


class UserIncludeSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    fullname = ser.CharField(help_text='Display name used in the general user interface')
    links = LinksFieldWIthSelfLink({'html': 'absolute_url'})

    def absolute_url(self, obj):
        return obj.absolute_url

    class Meta:
        type_ = 'users'


class OtherObjectIncludeSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    links = LinksFieldWIthSelfLink({'html': 'absolute_url'})

    def absolute_url(self, obj):
        return obj.absolute_url

    class Meta:
        type_ = 'objects'


def _params_url_val(val, obj, serializer, request, allowed_params, **kwargs):

    if isinstance(val, Attribute):
        return val.resolve_attribute(obj, request, allowed_params)
    if isinstance(val, Link):  # If a Link is passed, get the url value
        return val.resolve_url(obj, **kwargs)
    elif isinstance(val, basestring):  # if a string is passed, it's a method of the serializer
        return getattr(serializer, val)(obj)
    else:
        return val


class AttributeLinksField(LinksField):

    def __init__(self, objects, *args, **kwargs):
        ser.Field.__init__(self, read_only=True, *args, **kwargs)
        self.objects = objects

    def to_representation(self, obj, link_endpoint=None, link_kwargs=None):
        if hasattr(obj, 'title'):
            allowed_params = ['children', 'contributors', 'pointers', 'registrations']
        else:
            allowed_params = ['nodes']
        ret = _rapply(self.objects, _params_url_val, obj=obj, serializer=self.parent,
                      request=self.context.get('request'), allowed_params=allowed_params)
        if hasattr(obj, 'get_absolute_url'):
            ret['self'] = obj.get_absolute_url()
        if hasattr(obj, 'link'):
            _url_val(obj.link, obj, self.parent)
        return ret


class Attribute(object):

    def __init__(self, name, query=None):
        self.name = name
        self.query = query

    def resolve_attribute(self, obj, request, allowed_params):
        ret = {}
        if self.query:
            object_list = getattr(obj, self.query)
        else:
            auth = self.get_user_auth(request)
            get_object = getattr(self, 'get_{}'.format(self.name))
            object_list = get_object(obj, auth)
        if 'include' in request.query_params:
            include_params = request.query_params['include'].split(',')
            for param in include_params:
                if param not in allowed_params:
                    raise ValidationError('{} is not a valid additional query parameter.'.format(param))
            if self.name in include_params:
                ret = self.process_objects(object_list)
        ret['count'] = len(object_list)
        return ret

    def process_objects(self, object_list):
        objects_serialized = []
        for o in object_list:
            if hasattr(o, 'title'):
                objects_serialized.append(NodeIncludeSerializer(o).data)
            else:
                objects_serialized.append(UserIncludeSerializer(o).data)
        return {'list': objects_serialized}

    def get_children(self, obj, auth):
        nodes = [node for node in obj.nodes if node.can_view(auth) and node.primary]
        return nodes

    def get_nodes(self, obj, auth):
        query = (
            Q('contributors', 'eq', obj) &
            Q('is_folder', 'ne', True) &
            Q('is_deleted', 'ne', True)
        )
        raw_nodes = Node.find(query)
        nodes = [each for each in raw_nodes if each.is_public]
        return nodes

    def get_registrations(self, obj, auth):
        registrations = [node for node in obj.node__registrations if node.can_view(auth)]
        return registrations

    # todo add authorization check for user pages
    def get_user_auth(self, request):
        if request is None:
            return Auth(None)
        user = request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        return auth
