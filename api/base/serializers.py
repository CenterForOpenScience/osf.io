import collections
import re

from .mixins import IncludeParametersMixin
from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError
from website.util.sanitize import strip_html
from api.base.utils import absolute_reverse, waterbutler_url_for
from django.core.urlresolvers import NoReverseMatch
from django.core.exceptions import ImproperlyConfigured

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


class HyperlinkedIdentityFieldWithMeta(ser.HyperlinkedIdentityField):
    # Returns a list with a url and an optional hash containing additional meta information

    def __init__(self, view_name=None, **kwargs):
        kwargs['read_only'] = True
        kwargs['source'] = '*'
        self.meta = kwargs.pop('meta', None)
        super(ser.HyperlinkedIdentityField, self).__init__(view_name, **kwargs)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        # Unsaved objects will not yet have a valid URL.
        if obj.pk is None:
            return None

        lookup_value = getattr(obj, self.lookup_field)

        if lookup_value is None:
            return None

        kwargs = {self.lookup_url_kwarg: lookup_value}
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

    def to_representation(self, value):
        request = self.context.get('request', None)
        format = self.context.get('format', None)

        assert request is not None, (
            "`%s` requires the request in the serializer"
            " context. Add `context={'request': request}` when instantiating "
            "the serializer." % self.__class__.__name__
        )

        if format and self.format and self.format != format:
            format = self.format

        # Return the hyperlink, or error if incorrectly configured.
        try:
            if self.meta is not None:
                meta = {}
                for key in self.meta:
                    meta[key] = _rapply(self.meta.values()[0], _url_val, obj=value, serializer=self.parent)
                self.meta = meta
            return [self.get_url(value, self.view_name, request, format), self.meta]
        except NoReverseMatch:
            msg = (
                'Could not resolve URL for hyperlinked relationship using '
                'view name "%s". You may have failed to include the related '
                'model in your API, or incorrectly configured the '
                '`lookup_field` attribute on this field.'
            )
            raise ImproperlyConfigured(msg % self.view_name)


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
            self.child.to_representation(item) for item in data
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
    def to_representation(self, obj):
        """Serialize to final representation.

        :param obj: Object to be serialized.
        :param envelope: Key for resource object.
        """
        if 'include' in self.context['request'].query_params:
            view_class = self.context['view'] if 'view' in self.context else None
            base_view_classes = view_class.__class__.__bases__
            if IncludeParametersMixin not in base_view_classes:
                raise ValidationError('Include query parameters are not supported in this request.')

            super(view_class, self).process_includes(self.context['request'].query_params['include'].split(','))
        data = super(JSONAPISerializer, self).to_representation(obj)
        return data

    # overrides Serializer: Add HTML-sanitization similar to that used by APIv1 front-end views
    def is_valid(self, clean_html=True, **kwargs):
        """After validation, scrub HTML from validated_data prior to saving (for create and update views)"""
        ret = super(JSONAPISerializer, self).is_valid(**kwargs)

        if clean_html is True:
            self._validated_data = _rapply(self.validated_data, strip_html)
        return ret
