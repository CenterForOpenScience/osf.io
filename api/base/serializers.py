import re
import collections

from rest_framework import exceptions
from rest_framework import serializers as ser
from rest_framework.fields import SkipField

from framework.auth import core as auth_core
from website import settings
from website.util.sanitize import strip_html
from website.util import waterbutler_api_url_for
from rest_framework.fields import get_attribute as get_nested_attributes

from api.base import utils
from api.base.settings import BULK_SETTINGS
from api.base.exceptions import InvalidQueryStringError, Conflict, JSONAPIException


def format_relationship_links(related_link=None, self_link=None, rel_meta=None, self_meta=None):
    """
    Properly handles formatting of self and related links according to JSON API.

    Removes related or self link, if none.
    """

    ret = {'links': {}}

    if related_link:
        ret['links'].update({
            'related': {
                'href': related_link or {},
                'meta': rel_meta or {}
            }
        })

    if self_link:
        ret['links'].update({
            'self': {
                'href': self_link or {},
                'meta': self_meta or {}
            }
        })

    return ret


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
    """
    ID field that validates that 'id' in the request body is the same as the instance 'id' for single requests.
    """
    def __init__(self, **kwargs):
        kwargs['label'] = 'ID'
        super(IDField, self).__init__(**kwargs)

    #Overrides CharField
    def to_internal_value(self, data):
        request = self.context['request']
        if request.method in utils.UPDATE_METHODS and not utils.is_bulk_request(request):
            id_field = getattr(self.root.instance, self.source, '_id')
            if id_field != data:
                raise Conflict()
        return super(IDField, self).to_internal_value(data)


class TypeField(ser.CharField):
    """
    Type field that validates that 'type' in the request body is the same as the Meta type.

    Also ensures that type is write-only and required.
    """
    def __init__(self, **kwargs):
        kwargs['write_only'] = True
        kwargs['required'] = True
        super(TypeField, self).__init__(**kwargs)

    # Overrides CharField
    def to_internal_value(self, data):
        if isinstance(self.root, JSONAPIListSerializer):
            type_ = self.root.child.Meta.type_
        else:
            type_ = self.root.Meta.type_

        if type_ != data:
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


class AuthorizedCharField(ser.CharField):
    """
    Passes auth of the logged-in user to the object's method
    defined as the field source.

    Example:
        content = AuthorizedCharField(source='get_content')
    """
    def __init__(self, source=None, **kwargs):
        assert source is not None, 'The `source` argument is required.'
        self.source = source
        super(AuthorizedCharField, self).__init__(source=self.source, **kwargs)

    def get_attribute(self, obj):
        user = self.context['request'].user
        auth = auth_core.Auth(user)
        field_source_method = getattr(obj, self.source)
        return field_source_method(auth=auth)


class RelationshipField(ser.HyperlinkedIdentityField):
    """
    RelationshipField that permits the return of both self and related links, along with optional
    meta information.

    Example:
    children = RelationshipField(
        related_view='nodes:node-children',
        related_view_kwargs={'node_id': '<pk>'},
        self_view='nodes:node-node-children-relationship',
        self_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_node_count'}
    )

    The lookup field must be surrounded in angular brackets to find the attribute on the target. Otherwise, the lookup
    field will be returned verbatim.

    Example:
     wiki_home = RelationshipField(
        related_view='addon:addon-detail',
        related_view_kwargs={'node_id': '<_id>', 'provider': 'wiki'},
    )
    '_id' is enclosed in angular brackets, but 'wiki' is not. 'id' will be looked up on the target, but 'wiki' will not.
     The serialized result would be '/nodes/abc12/addons/wiki'.

    Field can handle nested attributes:

    Example:
    wiki_home = RelationshipField(
        related_view='wiki:wiki-detail',
        related_view_kwargs={'node_id': '<_id>', 'wiki_id': '<wiki_pages_current.home>'}
    )

    """
    embeddable = True
    json_api_link = True  # serializes to a links object

    def __init__(self, related_view=None, related_view_kwargs=None, self_view=None, self_view_kwargs=None,
                 self_meta=None, related_meta=None, always_embed=False, **kwargs):
        related_view = related_view
        self_view = self_view
        related_kwargs = related_view_kwargs
        self_kwargs = self_view_kwargs
        self.views = {'related': related_view, 'self': self_view}
        self.view_kwargs = {'related': related_kwargs, 'self': self_kwargs}
        self.related_meta = related_meta
        self.self_meta = self_meta
        self.always_embed = always_embed
        assert (related_view is not None or self_view is not None), 'Self or related view must be specified.'
        if related_view:
            assert related_kwargs is not None, 'Must provide related view kwargs.'
            assert isinstance(related_kwargs, dict), "Related view kwargs must have format {'lookup_url_kwarg: lookup_field}."
        if self_view:
            assert self_kwargs is not None, 'Must provide self view kwargs.'
            assert isinstance(self_kwargs, dict), "Self view kwargs must have format {'lookup_url_kwarg: lookup_field}."

        view_name = related_view
        if view_name:
            lookup_kwarg = related_kwargs.keys()[0]
            lookup_field = related_kwargs.values()[0]
        else:
            view_name = self_view
            lookup_kwarg = self_kwargs.keys()[0]
            lookup_field = self_kwargs.values()[0]

        super(RelationshipField, self).__init__(view_name, lookup_url_kwarg=lookup_kwarg, lookup_field=lookup_field, **kwargs)

    def get_meta_information(self, meta_data, value):
        """
        For retrieving meta values, otherwise returns {}
        """
        meta = {}
        for key in meta_data or {}:
            if key == 'count':
                show_related_counts = self.context['request'].query_params.get('related_counts', False)
                if utils.is_truthy(show_related_counts):
                    meta[key] = _rapply(meta_data[key], _url_val, obj=value, serializer=self.parent)
                elif utils.is_falsy(show_related_counts):
                    continue
                if not utils.is_truthy(show_related_counts):
                    raise InvalidQueryStringError(
                        detail="Acceptable values for the related_counts query param are 'true' or 'false'; got '{0}'".format(show_related_counts),
                        parameter='related_counts'
                    )
            else:
                meta[key] = _rapply(meta_data[key], _url_val, obj=value, serializer=self.parent)
        return meta

    def lookup_attribute(self, obj, lookup_field):
        """
        Returns attribute from target object unless attribute surrounded in angular brackets where it returns the lookup field.

        Also handles the lookup of nested attributes.
        """
        bracket_check = _tpl(lookup_field)
        if bracket_check:
            source_attrs = bracket_check.split('.')
            return get_nested_attributes(obj, source_attrs)
        return lookup_field

    def kwargs_lookup(self, obj, kwargs_dict):
        """
        For returning kwargs dictionary of format {"lookup_url_kwarg": lookup_value}
        """
        kwargs_retrieval = {}
        for lookup_url_kwarg, lookup_field in kwargs_dict.items():
            try:
                lookup_value = self.lookup_attribute(obj, lookup_field)
            except AttributeError as exc:
                raise AssertionError(exc)
            if lookup_value is None:
                return None
            kwargs_retrieval[lookup_url_kwarg] = lookup_value
        return kwargs_retrieval

    # Overrides HyperlinkedIdentityField
    def get_url(self, obj, view_name, request, format):
        urls = {}
        for view_name, view in self.views.items():
            if view is None:
                urls[view_name] = {}
            else:
                kwargs = self.kwargs_lookup(obj, self.view_kwargs[view_name])
                if kwargs is None:
                    urls[view_name] = {}
                else:
                    urls[view_name] = self.reverse(view, kwargs=kwargs, request=request, format=format)

        if not urls['self'] and not urls['related']:
            urls = None
        return urls

    def to_esi_representation(self, value):
        url = super(RelationshipField, self).to_representation(value)
        if url:
            return '<esi:include src="{}?format=jsonapi"/>'.format(url)
        return self.to_representation(value)

    # Overrides HyperlinkedIdentityField
    def to_representation(self, value):
        urls = super(RelationshipField, self).to_representation(value)
        if not urls:
            ret = None
        else:
            related_url = urls['related']
            related_meta = self.get_meta_information(self.related_meta, value)
            self_url = urls['self']
            self_meta = self.get_meta_information(self.self_meta, value)

            ret = format_relationship_links(related_url, self_url, related_meta, self_meta)

        return ret


class JSONAPIHyperlinkedGuidRelatedField(ser.Field):
    """
    Field that returns a nested dict with the url (constructed based
    on the object's type), optional meta information, and link_type.

    Example:

        target = JSONAPIHyperlinkedGuidRelatedField(link_type='related', meta={'type': 'get_target_type'})

    """
    json_api_link = True  # serializes to a links object

    def __init__(self, **kwargs):
        self.meta = kwargs.pop('meta', {})
        self.link_type = kwargs.pop('link_type', 'url')
        super(JSONAPIHyperlinkedGuidRelatedField, self).__init__(read_only=True, **kwargs)

    def to_esi_representation(self, value):
        url = super(JSONAPIHyperlinkedGuidRelatedField, self).to_representation(value)
        if url:
            return '<esi:include src="{}?format=jsonapi"/>'.format(url)
        return self.to_representation(value)

    def to_representation(self, value):
        """
        Returns nested dictionary in format {'links': {'self.link_type': ... }

        If no meta information, self.link_type is equal to a string containing link's URL.  Otherwise,
        the link is represented as a links object with 'href' and 'meta' members.
        """
        meta = _rapply(self.meta, _url_val, obj=value, serializer=self.parent)
        return {'links': {self.link_type: {'href': value.get_absolute_url(), 'meta': meta}}}


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


class NodeFileHyperLinkField(RelationshipField):
    def __init__(self, kind=None, never_embed=False, **kws):
        self.kind = kind
        self.never_embed = never_embed
        super(NodeFileHyperLinkField, self).__init__(**kws)

    def get_url(self, obj, view_name, request, format):
        if self.kind and obj.kind != self.kind:
            return {}
        return super(NodeFileHyperLinkField, self).get_url(obj, view_name, request, format)


class JSONAPIListSerializer(ser.ListSerializer):

    def to_representation(self, data):
        # Don't envelope when serializing collection
        return [
            self.child.to_representation(item, envelope=None) for item in data
        ]

    # Overrides ListSerializer which doesn't support multiple update by default
    def update(self, instance, validated_data):
        if len(instance) != len(validated_data):
            raise exceptions.ValidationError({'non_field_errors': 'Could not find all objects to update.'})

        id_lookup = self.child.fields['id'].source
        instance_mapping = {getattr(item, id_lookup): item for item in instance}
        data_mapping = {item.get(id_lookup): item for item in validated_data}

        ret = []

        for resource_id, data in data_mapping.items():
            resource = instance_mapping.get(resource_id, None)
            ret.append(self.child.update(resource, data))

        return ret

    # overrides ListSerializer
    def run_validation(self, data):
        meta = getattr(self, 'Meta', None)
        bulk_limit = getattr(meta, 'bulk_limit', BULK_SETTINGS['DEFAULT_BULK_LIMIT'])

        num_items = len(data)

        if num_items > bulk_limit:
            raise JSONAPIException(source={'pointer': '/data'},
                                   detail='Bulk operation limit is {}, got {}.'.format(bulk_limit, num_items))

        return super(JSONAPIListSerializer, self).run_validation(data)

    # overrides ListSerializer: Add HTML-sanitization similar to that used by APIv1 front-end views
    def is_valid(self, clean_html=True, **kwargs):
        """
        After validation, scrub HTML from validated_data prior to saving (for create and update views)

        Exclude 'type' from validated_data.

        """
        ret = super(JSONAPIListSerializer, self).is_valid(**kwargs)

        if clean_html is True:
            self._validated_data = _rapply(self.validated_data, strip_html)

        for data in self._validated_data:
            data.pop('type', None)

        return ret


class JSONAPISerializer(ser.Serializer):
    """Base serializer. Requires that a `type_` option is set on `class Meta`. Also
    allows for enveloping of both single resources and collections.  Looks to nest fields
    according to JSON API spec. Relational fields must set json_api_link=True flag.
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

        data = collections.OrderedDict([
            ('id', ''),
            ('type', type_),
            ('attributes', collections.OrderedDict()),
            ('relationships', collections.OrderedDict()),
            ('embeds', {}),
            ('links', {}),
        ])

        embeds = self.context.get('embed', {})
        esi = self.context.get('esi', {})
        fields = [field for field in self.fields.values() if not field.write_only]

        for item in set(embeds.keys()) - set([f.field_name for f in fields if getattr(f, 'json_api_link', False)]):
            raise InvalidQueryStringError(
                detail="Field '{0}' is not embeddable.".format(item),
                parameter='embed'
            )

        for field in fields:
            try:
                attribute = field.get_attribute(obj)
            except SkipField:
                continue

            if getattr(field, 'json_api_link', False):
                # If embed=field_name is appended to the query string or 'always_embed' flag is True, directly embed the
                # results rather than adding a relationship link
                if embeds and (field.field_name in embeds or getattr(field, 'always_embed', None)):
                    if esi:
                        result = field.to_esi_representation(attribute)
                    else:
                        result = self.context['embed'][field.field_name](obj)
                    if result:
                        data['embeds'][field.field_name] = result
                else:
                    result = field.to_representation(attribute)
                    if result:
                        data['relationships'][field.field_name] = result
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

        if not data['embeds']:
            del data['embeds']

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

        if self.context['request'].method in utils.UPDATE_METHODS:
            self._validated_data.pop('_id', None)

        return ret


def DevOnly(field):
    """Make a field only active in ``DEV_MODE``. ::

        experimental_field = DevMode(CharField(required=False))
    """
    return field if settings.DEV_MODE else None
