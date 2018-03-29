import collections
import re
from urlparse import urlparse

import furl
from django.core.urlresolvers import resolve, reverse, NoReverseMatch
from django.core.exceptions import ImproperlyConfigured
from django.utils import six

from rest_framework import exceptions, permissions
from rest_framework import serializers as ser
from rest_framework.fields import SkipField
from rest_framework.fields import get_attribute as get_nested_attributes
from rest_framework.mixins import RetrieveModelMixin

from api.base import utils
from osf.utils import permissions as osf_permissions
from osf.utils import sanitize
from api.base import exceptions as api_exceptions
from api.base.settings import BULK_SETTINGS
from framework.auth import core as auth_core
from osf.models import AbstractNode, MaintenanceState
from website import settings
from website.project.model import has_anonymous_link


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


def is_anonymized(request):
    if hasattr(request, '_is_anonymized'):
        return request._is_anonymized
    private_key = request.query_params.get('view_only', None)
    request._is_anonymized = osf_permissions.check_private_key_for_anonymized_link(private_key)
    return request._is_anonymized


class ConditionalField(ser.Field):
    """
    Skips the inner field based on `should_show` or `should_hide`; override whichever makes the logic more readable.
    If you'd prefer to return `None` rather skipping the field, override `should_be_none` as well.
    """

    def __init__(self, field, **kwargs):
        super(ConditionalField, self).__init__(**kwargs)
        self.field = field
        self.source = self.field.source
        self.required = self.field.required
        self.read_only = self.field.read_only

    def should_show(self, instance):
        return not self.should_hide(instance)

    def should_hide(self, instance):
        raise NotImplementedError()

    def should_be_none(self, instance):
        return False

    def get_attribute(self, instance):
        if not self.should_show(instance):
            if self.should_be_none(instance):
                return None
            raise SkipField
        return self.field.get_attribute(instance)

    def bind(self, field_name, parent):
        super(ConditionalField, self).bind(field_name, parent)
        self.field.bind(field_name, self)

    def to_representation(self, value):
        if getattr(self.field.root, 'child', None):
            self.field.parent = self.field.root.child
        else:
            self.field.parent = self.field.root
        return self.field.to_representation(value)

    def to_esi_representation(self, value, envelope='data'):
        if getattr(self.field.root, 'child', None):
            self.field.parent = self.field.root.child
        else:
            self.field.parent = self.field.root
        return self.field.to_esi_representation(value, envelope)

    def to_internal_value(self, data):
        return self.field.to_internal_value(data)


class ShowIfVersion(ConditionalField):
    """
    Skips the field if the specified request version is not after a feature's earliest supported version,
    or not before the feature's latest supported version.
    """

    def __init__(self, field, min_version, max_version, **kwargs):
        super(ShowIfVersion, self).__init__(field, **kwargs)
        self.min_version = min_version
        self.max_version = max_version
        self.help_text = 'This field is deprecated as of version {}'.format(self.max_version) or kwargs.get('help_text')

    def should_hide(self, instance):
        request = self.context.get('request')
        return request and utils.is_deprecated(request.version, self.min_version, self.max_version)


class ShowIfCurrentUser(ConditionalField):

    def should_show(self, instance):
        request = self.context.get('request')
        return request and request.user == instance


class HideIfRegistration(ConditionalField):
    """
    If node is a registration, this field will return None.
    """

    def should_hide(self, instance):
        return instance.is_registration

    def should_be_none(self, instance):
        return not isinstance(self.field, RelationshipField)


class HideIfDisabled(ConditionalField):
    """
    If the user is disabled, returns None for attribute fields, or skips
    if a RelationshipField.
    """

    def should_hide(self, instance):
        return instance.is_disabled

    def should_be_none(self, instance):
        return not isinstance(self.field, RelationshipField)


class HideIfWithdrawal(ConditionalField):
    """
    If registration is withdrawn, this field will return None.
    """

    def should_hide(self, instance):
        return instance.is_retracted

    def should_be_none(self, instance):
        return not isinstance(self.field, RelationshipField)


class HideIfNotNodePointerLog(ConditionalField):
    """
    This field will not be shown if the log is not a pointer log for a node
    """
    def should_hide(self, instance):
        pointer_param = instance.params.get('pointer', False)
        if pointer_param:
            node = AbstractNode.load(pointer_param['id'])
            if node:
                return node.type != 'osf.node'
        return True


class HideIfNotRegistrationPointerLog(ConditionalField):
    """
    This field will not be shown if the log is not a pointer log for a registration
    """

    def should_hide(self, instance):
        pointer_param = instance.params.get('pointer', False)
        if pointer_param:
            node = AbstractNode.load(pointer_param['id'])
            if node:
                return node.type != 'osf.registration'
        return True


class HideIfProviderCommentsAnonymous(ConditionalField):
    """
    If the action's provider has anonymous comments and the user does not have `view_actions`
    permission on the provider, hide the field.
    """

    def should_hide(self, instance):
        request = self.context.get('request')
        auth = utils.get_user_auth(request)
        if auth.logged_in:
            provider = instance.target.provider
            if provider.reviews_comments_anonymous is False or auth.user.has_perm('view_actions', provider):
                return False
        return True


class HideIfProviderCommentsPrivate(ConditionalField):
    """
    If the action's provider has private comments and the user does not have `view_actions`
    permission on the provider, hide the field.
    """

    def should_hide(self, instance):
        request = self.context.get('request')
        auth = utils.get_user_auth(request)
        if auth.logged_in:
            provider = instance.target.provider
            if provider.reviews_comments_private is False or auth.user.has_perm('view_actions', provider):
                return False
        return True


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


def _url_val(val, obj, serializer, request, **kwargs):
    """Function applied by `HyperlinksField` to get the correct value in the
    schema.
    """
    url = None
    if isinstance(val, Link):  # If a Link is passed, get the url value
        url = val.resolve_url(obj, request)
    elif isinstance(val, basestring):  # if a string is passed, it's a method of the serializer
        if getattr(serializer, 'field', None):
            serializer = serializer.parent
        url = getattr(serializer, val)(obj) if obj is not None else None
    else:
        url = val

    if not url and url != 0:
        raise SkipField
    else:
        return url


class VersionedDateTimeField(ser.DateTimeField):
    """
    Custom DateTimeField that forces dates into the ISO-8601 format with timezone information in version 2.2.
    """

    def to_representation(self, value):
        request = self.context.get('request')
        if request:
            if request.version >= '2.2':
                self.format = '%Y-%m-%dT%H:%M:%S.%fZ'
            else:
                self.format = '%Y-%m-%dT%H:%M:%S.%f' if value.microsecond else '%Y-%m-%dT%H:%M:%S'
        return super(VersionedDateTimeField, self).to_representation(value)


class IDField(ser.CharField):
    """
    ID field that validates that 'id' in the request body is the same as the instance 'id' for single requests.
    """

    def __init__(self, **kwargs):
        kwargs['label'] = 'ID'
        super(IDField, self).__init__(**kwargs)

    # Overrides CharField
    def to_internal_value(self, data):
        request = self.context.get('request')
        if request:
            if request.method in utils.UPDATE_METHODS and not utils.is_bulk_request(request):
                id_field = self.get_id(self.root.instance)
                if id_field != data:
                    raise api_exceptions.Conflict(detail=('The id you used in the URL, "{}", does not match the id you used in the json body\'s id field, "{}". The object "{}" exists, otherwise you\'d get a 404, so most likely you need to change the id field to match.'.format(id_field, data, id_field)))
        return super(IDField, self).to_internal_value(data)

    def get_id(self, obj):
        return getattr(obj, self.source, '_id')


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
            raise api_exceptions.Conflict(detail=('This resource has a type of "{}", but you set the json body\'s type field to "{}". You probably need to change the type field to match the resource\'s type.'.format(type_, data)))
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
            raise api_exceptions.Conflict(detail=('The target resource has a type of "{}", but you set the json body\'s type field to "{}".  You probably need to change the type field to match the target resource\'s type.'.format(self.target_type, data)))
        return super(TargetTypeField, self).to_internal_value(data)


class JSONAPIListField(ser.ListField):
    def to_internal_value(self, data):
        if not isinstance(data, list):
            self.fail('not_a_list', input_type=type(data).__name__)

        return super(JSONAPIListField, self).to_internal_value(data)


class ValuesListField(JSONAPIListField):
    """
    JSONAPIListField that uses a values_list with flat=True to return just
    an array of the specified field (attr_name) for optimization purposes.
    """
    def __init__(self, **kwargs):
        self.attr_name = kwargs.pop('attr_name')
        super(ValuesListField, self).__init__(**kwargs)

    def to_representation(self, val):
        return val.values_list(self.attr_name, flat=True)


class AuthorizedCharField(ser.CharField):
    """
    Passes auth of the logged-in user to the object's method
    defined as the field source.

    Example:
        content = AuthorizedCharField(source='get_content')
    """

    def __init__(self, source, **kwargs):
        self.source = source
        super(AuthorizedCharField, self).__init__(source=self.source, **kwargs)

    def get_attribute(self, obj):
        user = self.context['request'].user
        auth = auth_core.Auth(user)
        field_source_method = getattr(obj, self.source)
        return field_source_method(auth=auth)

class AnonymizedRegexField(AuthorizedCharField):
    """
    Performs a regex replace on the content of the authorized object's
    source field when an anonymous view is requested.

    Example:
        content = AnonymizedRegexField(source='get_content', regex='\[@[^\]]*\]\([^\) ]*\)', replace='@A User')
    """

    def __init__(self, source, regex, replace, **kwargs):
        self.source = source
        self.regex = regex
        self.replace = replace
        super(AnonymizedRegexField, self).__init__(source=self.source, **kwargs)

    def get_attribute(self, obj):
        value = super(AnonymizedRegexField, self).get_attribute(obj)

        if value:
            user = self.context['request'].user
            auth = auth_core.Auth(user)
            if 'view_only' in self.context['request'].query_params:
                auth.private_key = self.context['request'].query_params['view_only']
                if has_anonymous_link(obj.node, auth):
                    value = re.sub(self.regex, self.replace, value)

        return value

class RelationshipField(ser.HyperlinkedIdentityField):
    """
    RelationshipField that permits the return of both self and related links, along with optional
    meta information. ::

        children = RelationshipField(
            related_view='nodes:node-children',
            related_view_kwargs={'node_id': '<_id>'},
            self_view='nodes:node-node-children-relationship',
            self_view_kwargs={'node_id': '<_id>'},
            related_meta={'count': 'get_node_count'}
        )

    The lookup field must be surrounded in angular brackets to find the attribute on the target. Otherwise, the lookup
    field will be returned verbatim. ::

        wiki_home = RelationshipField(
            related_view='addon:addon-detail',
            related_view_kwargs={'node_id': '<_id>', 'provider': 'wiki'},
        )

    '_id' is enclosed in angular brackets, but 'wiki' is not. 'id' will be looked up on the target, but 'wiki' will not.
     The serialized result would be '/nodes/abc12/addons/wiki'.

    Field can handle nested attributes: ::

        wiki_home = RelationshipField(
            related_view='wiki:wiki-detail',
            related_view_kwargs={'node_id': '<_id>', 'wiki_id': '<wiki_pages_current.home>'}
        )

    Field can handle a filter_key, which operates as the source field (but
    is named differently to not interfere with HyperLinkedIdentifyField's source

    The ``filter_key`` argument defines the Mongo key (or ODM field name) to filter on
    when using the ``FilterMixin`` on a view. ::

        parent = RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<parent_node._id>'},
            filter_key='parent_node'
        )

    Field can include optional filters:

    Example:
    replies = RelationshipField(
        self_view='nodes:node-comments',
        self_view_kwargs={'node_id': '<node._id>'},
        filter={'target': '<_id>'})
    )
    """
    json_api_link = True  # serializes to a links object

    def __init__(self, related_view=None, related_view_kwargs=None, self_view=None, self_view_kwargs=None,
                 self_meta=None, related_meta=None, always_embed=False, filter=None, filter_key=None, required=False, **kwargs):
        related_view = related_view
        self_view = self_view
        related_kwargs = related_view_kwargs
        self_kwargs = self_view_kwargs
        self.views = {'related': related_view, 'self': self_view}
        self.view_kwargs = {'related': related_kwargs, 'self': self_kwargs}
        self.related_meta = related_meta
        self.self_meta = self_meta
        self.always_embed = always_embed
        self.filter = filter
        self.filter_key = filter_key

        assert (related_view is not None or self_view is not None), 'Self or related view must be specified.'
        if related_view:
            assert related_kwargs is not None, 'Must provide related view kwargs.'
            if not callable(related_kwargs):
                assert isinstance(related_kwargs,
                                  dict), "Related view kwargs must have format {'lookup_url_kwarg: lookup_field}."
        if self_view:
            assert self_kwargs is not None, 'Must provide self view kwargs.'
            assert isinstance(self_kwargs, dict), "Self view kwargs must have format {'lookup_url_kwarg: lookup_field}."

        view_name = related_view
        if view_name:
            lookup_kwargs = related_kwargs
        else:
            view_name = self_view
            lookup_kwargs = self_kwargs
        if kwargs.get('lookup_url_kwarg', None):
            lookup_kwargs = kwargs.pop('lookup_url_kwarg')
        super(RelationshipField, self).__init__(view_name, lookup_url_kwarg=lookup_kwargs, **kwargs)

        # Allow a RelationshipField to be modified if explicitly set so
        if kwargs.get('read_only') is not None:
            self.read_only = kwargs['read_only']

        # Allow a RelationshipField to be required
        if required:
            assert not self.read_only, 'May not set both `read_only` and `required`'
            self.required = required

    def resolve(self, resource, field_name, request):
        """
        Resolves the view when embedding.
        """
        lookup_url_kwarg = self.lookup_url_kwarg
        if callable(lookup_url_kwarg):
            lookup_url_kwarg = lookup_url_kwarg(getattr(resource, field_name))

        kwargs = {attr_name: self.lookup_attribute(resource, attr) for (attr_name, attr) in lookup_url_kwarg.items()}
        kwargs.update({'version': request.parser_context['kwargs']['version']})

        view = self.view_name
        if callable(self.view_name):
            view = view(getattr(resource, field_name))
        return resolve(
            reverse(
                view,
                kwargs=kwargs
            )
        )

    def process_related_counts_parameters(self, params, value):
        """
        Processes related_counts parameter.

        Can either be a True/False value for fetching counts on all fields, or a comma-separated list for specifying
        individual fields.  Ensures field for which we are requesting counts is a relationship field.
        """
        if utils.is_truthy(params) or utils.is_falsy(params):
            return params

        field_counts_requested = [val for val in params.split(',')]

        countable_fields = {field for field in self.parent.fields if
                            getattr(self.parent.fields[field], 'json_api_link', False) or
                            getattr(getattr(self.parent.fields[field], 'field', None), 'json_api_link', None)}
        for count_field in field_counts_requested:
            # Some fields will hide relationships, e.g. HideIfWithdrawal
            # Ignore related_counts for these fields
            fetched_field = self.parent.fields.get(count_field)

            hidden = fetched_field and isinstance(fetched_field, HideIfWithdrawal) and getattr(value, 'is_retracted', False)

            if not hidden and count_field not in countable_fields:
                raise api_exceptions.InvalidQueryStringError(
                    detail="Acceptable values for the related_counts query param are 'true', 'false', or any of the relationship fields; got '{0}'".format(
                        params),
                    parameter='related_counts'
                )
        return field_counts_requested

    def get_meta_information(self, meta_data, value):
        """
        For retrieving meta values, otherwise returns {}
        """
        meta = {}
        for key in meta_data or {}:
            if key == 'count' or key == 'unread':
                show_related_counts = self.context['request'].query_params.get('related_counts', False)
                if self.context['request'].parser_context.get('kwargs'):
                    if self.context['request'].parser_context['kwargs'].get('is_embedded'):
                        show_related_counts = False
                field_counts_requested = self.process_related_counts_parameters(show_related_counts, value)

                if utils.is_truthy(show_related_counts):
                    meta[key] = utils.rapply(meta_data[key], _url_val, obj=value, serializer=self.parent, request=self.context['request'])
                elif utils.is_falsy(show_related_counts):
                    continue
                elif self.field_name in field_counts_requested:
                    meta[key] = utils.rapply(meta_data[key], _url_val, obj=value, serializer=self.parent, request=self.context['request'])
                else:
                    continue
            elif key == 'projects_in_common':
                if not utils.get_user_auth(self.context['request']).user:
                    continue
                if not self.context['request'].query_params.get('show_projects_in_common', False):
                    continue
                meta[key] = utils.rapply(meta_data[key], _url_val, obj=value, serializer=self.parent, request=self.context['request'])
            else:
                meta[key] = utils.rapply(meta_data[key], _url_val, obj=value, serializer=self.parent, request=self.context['request'])
        return meta

    def lookup_attribute(self, obj, lookup_field):
        """
        Returns attribute from target object unless attribute surrounded in angular brackets where it returns the lookup field.

        Also handles the lookup of nested attributes.
        """
        bracket_check = _tpl(lookup_field)
        if bracket_check:
            source_attrs = bracket_check.split('.')
            # If you are using a nested attribute for lookup, and you get the attribute wrong, you will not get an
            # error message, you will just not see that field. This allows us to have slightly more dynamic use of
            # nested attributes in relationship fields.
            try:
                return_val = get_nested_attributes(obj, source_attrs)
            except KeyError:
                return None
            return return_val

        return lookup_field

    def kwargs_lookup(self, obj, kwargs_dict):
        """
        For returning kwargs dictionary of format {"lookup_url_kwarg": lookup_value}
        """
        if callable(kwargs_dict):
            kwargs_dict = kwargs_dict(obj)

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
                    if callable(view):
                        view = view(getattr(obj, self.field_name))
                    kwargs.update({'version': request.parser_context['kwargs']['version']})
                    url = self.reverse(view, kwargs=kwargs, request=request, format=format)
                    if self.filter:
                        formatted_filters = self.format_filter(obj)
                        if formatted_filters:
                            for filter in formatted_filters:
                                url = utils.extend_querystring_params(
                                    url,
                                    {'filter[{}]'.format(filter['field_name']): filter['value']}
                                )
                        else:
                            url = None

                    if url:
                        url = utils.extend_querystring_if_key_exists(url, self.context['request'],
                                                               'view_only')
                    urls[view_name] = url

        if not urls['self'] and not urls['related']:
            urls = None
        return urls

    def to_esi_representation(self, value, envelope='data'):
        relationships = self.to_representation(value)
        try:
            href = relationships['links']['related']['href']
        except KeyError:
            raise SkipField
        else:
            if href and not href == '{}':
                if self.always_embed:
                    envelope = 'data'
                query_dict = dict(format=['jsonapi', ], envelope=[envelope, ])
                if 'view_only' in self.parent.context['request'].query_params.keys():
                    query_dict.update(view_only=[self.parent.context['request'].query_params['view_only']])
                esi_url = utils.extend_querystring_params(href, query_dict)
                return '<esi:include src="{}"/>'.format(esi_url)

    def format_filter(self, obj):
        """ Take filters specified in self.filter and format them in a way that can be easily parametrized

        :param obj: RelationshipField object
        :return: list of dictionaries with 'field_name' and 'value' for each filter
        """
        filter_fields = self.filter.keys()
        filters = []
        for field_name in filter_fields:
            try:
                # check if serializer method passed in
                serializer_method = getattr(self.parent, self.filter[field_name])
            except AttributeError:
                value = self.lookup_attribute(obj, self.filter[field_name])
            else:
                value = serializer_method(obj)
            if not value:
                continue
            filters.append({'field_name': field_name, 'value': value})
        return filters if filters else None

    def to_internal_value(self, data):
        return data

    # Overrides HyperlinkedIdentityField
    def to_representation(self, value):
        request = self.context.get('request', None)
        format = self.context.get('format', None)

        assert request is not None, (
            '`%s` requires the request in the serializer'
            " context. Add `context={'request': request}` when instantiating "
            'the serializer.' % self.__class__.__name__
        )

        # By default use whatever format is given for the current context
        # unless the target is a different type to the source.
        #
        # Eg. Consider a HyperlinkedIdentityField pointing from a json
        # representation to an html property of that representation...
        #
        # '/snippets/1/' should link to '/snippets/1/highlight/'
        # ...but...
        # '/snippets/1/.json' should link to '/snippets/1/highlight/.html'
        if format and self.format and self.format != format:
            format = self.format

        # Return the hyperlink, or error if incorrectly configured.
        try:
            url = self.get_url(value, self.view_name, request, format)
        except NoReverseMatch:
            msg = (
                'Could not resolve URL for hyperlinked relationship using '
                'view name "%s". You may have failed to include the related '
                'model in your API, or incorrectly configured the '
                '`lookup_field` attribute on this field.'
            )
            if value in ('', None):
                value_string = {'': 'the empty string', None: 'None'}[value]
                msg += (
                    ' WARNING: The value of the field on the model instance '
                    "was %s, which may be why it didn't match any "
                    'entries in your URL conf.' % value_string
                )
            raise ImproperlyConfigured(msg % self.view_name)

        if url is None:
            raise SkipField

        related_url = url['related']
        related_path = urlparse(related_url).path
        related_meta = self.get_meta_information(self.related_meta, value)
        self_url = url['self']
        self_meta = self.get_meta_information(self.self_meta, value)
        relationship = format_relationship_links(related_url, self_url, related_meta, self_meta)
        if related_url and (len(related_path.split('/')) & 1) == 1:
            resolved_url = resolve(related_path)
            related_class = resolved_url.func.view_class
            if issubclass(related_class, RetrieveModelMixin):
                related_type = resolved_url.namespace
                try:
                    # TODO: change kwargs to preprint_provider_id and registration_id
                    if related_type == 'preprint_providers':
                        related_id = resolved_url.kwargs['provider_id']
                    elif related_type == 'registrations':
                        related_id = resolved_url.kwargs['node_id']
                    else:
                        related_id = resolved_url.kwargs[related_type[:-1] + '_id']
                except KeyError:
                    return relationship
                relationship['data'] = {'id': related_id, 'type': related_type}
        return relationship


class FileCommentRelationshipField(RelationshipField):
    def get_url(self, obj, view_name, request, format):
        if obj.kind == 'folder':
            raise SkipField
        return super(FileCommentRelationshipField, self).get_url(obj, view_name, request, format)


class TargetField(ser.Field):
    """
    Field that returns a nested dict with the url (constructed based
    on the object's type), optional meta information, and link_type.

    Example:

        target = TargetField(link_type='related', meta={'type': 'get_target_type'})

    """
    json_api_link = True  # serializes to a links object
    view_map = {
        'node': {
            'view': 'nodes:node-detail',
            'lookup_kwarg': 'node_id'
        },
        'comment': {
            'view': 'comments:comment-detail',
            'lookup_kwarg': 'comment_id'
        },
        'nodewikipage': {
            'view': None,
            'lookup_kwarg': None
        }
    }

    def __init__(self, **kwargs):
        self.meta = kwargs.pop('meta', {})
        self.link_type = kwargs.pop('link_type', 'url')
        super(TargetField, self).__init__(read_only=True, **kwargs)

    def resolve(self, resource, field_name, request):
        """
        Resolves the view for target node or target comment when embedding.
        """
        view_info = self.view_map.get(resource.target.referent._name, None)
        if not view_info:
            raise api_exceptions.TargetNotSupportedError('{} is not a supported target type'.format(
                resource.target._name
            ))
        if not view_info['view']:
            return None, None, None
        embed_value = resource.target._id

        return resolve(
            reverse(
                view_info['view'],
                kwargs={
                    view_info['lookup_kwarg']: embed_value,
                    'version': request.parser_context['kwargs']['version']
                }
            )
        )

    def to_esi_representation(self, value, envelope='data'):
        href = value.get_absolute_url()

        if href:
            esi_url = utils.extend_querystring_params(href, dict(envelope=[envelope, ], format=['jsonapi', ]))
            return '<esi:include src="{}"/>'.format(esi_url)
        return self.to_representation(value)

    def to_representation(self, value):
        """
        Returns nested dictionary in format {'links': {'self.link_type': ... }

        If no meta information, self.link_type is equal to a string containing link's URL.  Otherwise,
        the link is represented as a links object with 'href' and 'meta' members.
        """
        meta = utils.rapply(self.meta, _url_val, obj=value, serializer=self.parent, request=self.context['request'])
        return {'links': {self.link_type: {'href': value.referent.get_absolute_url(), 'meta': meta}}}


class LinksField(ser.Field):
    """Links field that resolves to a links object. Used in conjunction with `Link`.
    If the object to be serialized implements `get_absolute_url`, then the return value
    of that method is used for the `self` link.

    Example: ::

        links = LinksField({
            'html': 'absolute_url',
            'children': {
                'related': Link('nodes:node-children', node_id='<_id>'),
                'count': 'get_node_count'
            },
            'contributors': {
                'related': Link('nodes:node-contributors', node_id='<_id>'),
                'count': 'get_contrib_count'
            },
            'registrations': {
                'related': Link('nodes:node-registrations', node_id='<_id>'),
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

    def extend_absolute_info_url(self, obj):
        return utils.extend_querystring_if_key_exists(obj.get_absolute_info_url(), self.context['request'], 'view_only')

    def extend_absolute_url(self, obj):
        return utils.extend_querystring_if_key_exists(obj.get_absolute_url(), self.context['request'], 'view_only')

    def to_representation(self, obj):
        ret = {}
        for name, value in self.links.iteritems():
            try:
                url = _url_val(value, obj=obj, serializer=self.parent, request=self.context['request'])
            except SkipField:
                continue
            else:
                ret[name] = url
        if hasattr(obj, 'get_absolute_url') and 'self' not in self.links:
            ret['self'] = self.extend_absolute_url(obj)

        if 'info' in ret:
            if hasattr(obj, 'get_absolute_info_url'):
                ret['info'] = self.extend_absolute_info_url(obj)
            else:
                ret['info'] = utils.extend_querystring_if_key_exists(ret['info'], self.context['request'], 'view_only')

        return ret


class ListDictField(ser.DictField):

    def __init__(self, **kwargs):
        super(ListDictField, self).__init__(**kwargs)

    def to_representation(self, value):
        """
        Ensure the value of each key in the Dict to be a list
        """
        res = {}
        for key, val in value.items():
            if isinstance(self.child.to_representation(val), list):
                res[six.text_type(key)] = self.child.to_representation(val)
            else:
                if self.child.to_representation(val):
                    res[six.text_type(key)] = [self.child.to_representation(val)]
                else:
                    res[six.text_type(key)] = []
        return res


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
    URLs given an endpoint name and attributed enclosed in `<>`. This includes
    complex key strings like 'user.id'
    """

    def __init__(self, endpoint, args=None, kwargs=None, query_kwargs=None, **kw):
        self.endpoint = endpoint
        self.kwargs = kwargs or {}
        self.args = args or tuple()
        self.reverse_kwargs = kw
        self.query_kwargs = query_kwargs or {}

    def resolve_url(self, obj, request):
        kwarg_values = {key: _get_attr_from_tpl(attr_tpl, obj) for key, attr_tpl in self.kwargs.items()}
        kwarg_values.update({'version': request.parser_context['kwargs']['version']})
        arg_values = [_get_attr_from_tpl(attr_tpl, obj) for attr_tpl in self.args]
        query_kwarg_values = {key: _get_attr_from_tpl(attr_tpl, obj) for key, attr_tpl in self.query_kwargs.items()}
        # Presumably, if you have are expecting a value but the value is empty, then the link is invalid.
        for item in kwarg_values:
            if kwarg_values[item] is None:
                raise SkipField
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

    def resolve_url(self, obj, request):
        """Reverse URL lookup for WaterButler routes
        """
        if self.must_be_folder is True and not obj.path.endswith('/'):
            raise SkipField
        if self.must_be_file is True and obj.path.endswith('/'):
            raise SkipField

        if 'view_only' not in self.kwargs:
            view_only = request.query_params.get('view_only', False)
            if view_only:
                self.kwargs['view_only'] = view_only

        url = utils.waterbutler_api_url_for(obj.node._id, obj.provider, obj.path, **self.kwargs)
        if not url:
            raise SkipField
        else:
            return url


class NodeFileHyperLinkField(RelationshipField):
    def __init__(self, kind=None, never_embed=False, **kws):
        self.kind = kind
        self.never_embed = never_embed
        super(NodeFileHyperLinkField, self).__init__(**kws)

    def get_url(self, obj, view_name, request, format):
        if self.kind and obj.kind != self.kind:
            raise SkipField
        return super(NodeFileHyperLinkField, self).get_url(obj, view_name, request, format)


class JSONAPIListSerializer(ser.ListSerializer):
    def to_representation(self, data):
        enable_esi = self.context.get('enable_esi', False)
        envelope = self.context.update({'envelope': None})
        # Don't envelope when serializing collection
        errors = {}
        bulk_skip_uneditable = utils.is_truthy(self.context['request'].query_params.get('skip_uneditable', False))

        if isinstance(data, collections.Mapping):
            errors = data.get('errors', None)
            data = data.get('data', None)
        if enable_esi:
            ret = [
                self.child.to_esi_representation(item, envelope=None) for item in data
            ]
        else:
            ret = [
                self.child.to_representation(item, envelope=envelope) for item in data
            ]

        if errors and bulk_skip_uneditable:
            ret.append({'errors': errors})

        return ret

    # Overrides ListSerializer which doesn't support multiple update by default
    def update(self, instance, validated_data):

        # avoiding circular import
        from api.nodes.serializers import ContributorIDField

        # if PATCH request, the child serializer's partial attribute needs to be True
        if self.context['request'].method == 'PATCH':
            self.child.partial = True

        bulk_skip_uneditable = utils.is_truthy(self.context['request'].query_params.get('skip_uneditable', False))
        if not bulk_skip_uneditable:
            if len(instance) != len(validated_data):
                raise exceptions.ValidationError({'non_field_errors': 'Could not find all objects to update.'})

        id_lookup = self.child.fields['id'].source
        data_mapping = {item.get(id_lookup): item for item in validated_data}

        if isinstance(self.child.fields['id'], ContributorIDField):
            instance_mapping = {self.child.fields['id'].get_id(item): item for item in instance}
        else:
            instance_mapping = {getattr(item, id_lookup): item for item in instance}

        ret = {'data': []}

        for resource_id, resource in instance_mapping.items():
            data = data_mapping.pop(resource_id, None)
            ret['data'].append(self.child.update(resource, data))

        # If skip_uneditable in request, add validated_data for nodes in which the user did not have edit permissions to errors
        if data_mapping and bulk_skip_uneditable:
            ret.update({'errors': data_mapping.values()})
        return ret

    # overrides ListSerializer
    def run_validation(self, data):
        meta = getattr(self, 'Meta', None)
        bulk_limit = getattr(meta, 'bulk_limit', BULK_SETTINGS['DEFAULT_BULK_LIMIT'])

        num_items = len(data)

        if num_items > bulk_limit:
            raise api_exceptions.JSONAPIException(source={'pointer': '/data'},
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
            self._validated_data = utils.rapply(self.validated_data, sanitize.strip_html)

        for data in self._validated_data:
            data.pop('type', None)

        return ret


class SparseFieldsetMixin(object):
    def parse_sparse_fields(self, allow_unsafe=False, **kwargs):
        request = kwargs.get('context', {}).get('request', None)
        if request and (allow_unsafe or request.method in permissions.SAFE_METHODS):
            sparse_fieldset_query_param = 'fields[{}]'.format(self.Meta.type_)
            if sparse_fieldset_query_param in request.query_params:
                fieldset = request.query_params[sparse_fieldset_query_param].split(',')
                for field_name in self.fields.fields.copy().keys():
                    if field_name in ('id', 'links', 'type'):
                        # MUST return these fields
                        continue
                    if field_name not in fieldset:
                        self.fields.pop(field_name)

class BaseAPISerializer(ser.Serializer, SparseFieldsetMixin):

    def __init__(self, *args, **kwargs):
        self.parse_sparse_fields(**kwargs)
        super(BaseAPISerializer, self).__init__(*args, **kwargs)
        self.model_field_names = [name if field.source == '*' else field.source
                                  for name, field in self.fields.iteritems()]


class JSONAPISerializer(BaseAPISerializer):
    """Base serializer. Requires that a `type_` option is set on `class Meta`. Also
    allows for enveloping of both single resources and collections.  Looks to nest fields
    according to JSON API spec. Relational fields must set json_api_link=True flag.
    Self/html links must be nested under "links".
    """
    writeable_method_fields = frozenset([])

    # Don't serialize relationships that use these views
    # when viewing thru an anonymous VOL
    views_to_hide_if_anonymous = {
        'users:user-detail',
        'nodes:node-registrations',
    }

    # overrides Serializer
    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls(*args, **kwargs)
        return JSONAPIListSerializer(*args, **kwargs)

    def invalid_embeds(self, fields, embeds):
        fields_check = fields[:]
        for index, field in enumerate(fields_check):
            if getattr(field, 'field', None):
                fields_check[index] = field.field
        invalid_embeds = set(embeds.keys()) - set(
            [f.field_name for f in fields_check if getattr(f, 'json_api_link', False)])
        return invalid_embeds

    def to_esi_representation(self, data, envelope='data'):
        href = None
        query_params_blacklist = ['page[size]']
        href = self.get_absolute_url(data)
        if href and href != '{}':
            esi_url = furl.furl(href).add(args=dict(self.context['request'].query_params)).remove(
                args=query_params_blacklist).remove(args=['envelope']).add(args={'envelope': envelope}).url
            return '<esi:include src="{}"/>'.format(esi_url)
        # failsafe, let python do it if something bad happened in the ESI construction
        return super(JSONAPISerializer, self).to_representation(data)

    def run_validation(self, *args, **kwargs):
        # Overrides construtor for validated_data to allow writes to a SerializerMethodField
        # Validation for writeable SMFs is expected to happen in the model
        _validated_data = super(JSONAPISerializer, self).run_validation(*args, **kwargs)
        for field in self.writeable_method_fields:
            if field in self.initial_data:
                _validated_data[field] = self.initial_data[field]
        return _validated_data

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
        self.parse_sparse_fields(allow_unsafe=True, context=self.context)

        data = {
            'id': '',
            'type': type_,
            'attributes': {},
            'relationships': {},
            'embeds': {},
            'links': {},
        }

        embeds = self.context.get('embed', {})
        context_envelope = self.context.get('envelope', envelope)
        if context_envelope == 'None':
            context_envelope = None
        enable_esi = self.context.get('enable_esi', False)
        is_anonymous = is_anonymized(self.context['request'])
        to_be_removed = set()
        if is_anonymous and hasattr(self, 'non_anonymized_fields'):
            # Drop any fields that are not specified in the `non_anonymized_fields` variable.
            allowed = set(self.non_anonymized_fields)
            existing = set(self.fields.keys())
            to_be_removed = existing - allowed

        fields = [field for field in self.fields.values() if
                  not field.write_only and field.field_name not in to_be_removed]

        invalid_embeds = self.invalid_embeds(fields, embeds)
        invalid_embeds = invalid_embeds - to_be_removed
        if invalid_embeds:
            raise api_exceptions.InvalidQueryStringError(parameter='embed',
                                          detail='The following fields are not embeddable: {}'.format(
                                              ', '.join(invalid_embeds)))

        for field in fields:
            try:
                if hasattr(field, 'child_relation'):
                    attribute = field.child_relation.get_attribute(obj)
                else:
                    attribute = field.get_attribute(obj)
            except SkipField:
                continue

            if hasattr(field, 'child_relation'):
                nested_field = field.child_relation
            else:
                nested_field = getattr(field, 'field', None)
            if attribute is None:
                # We skip `to_representation` for `None` values so that
                # fields do not have to explicitly deal with that case.
                data['attributes'][field.field_name] = None
            else:
                try:
                    if hasattr(field, 'child_relation'):
                        if hasattr(attribute, 'all'):
                            representation = field.child_relation.to_representation(attribute.all())
                        else:
                            representation = field.child_relation.to_representation(attribute)
                    else:
                        if hasattr(attribute, 'all'):
                            representation = field.to_representation(attribute.all())
                        else:
                            representation = field.to_representation(attribute)
                except SkipField:
                    continue
                if getattr(field, 'json_api_link', False) or getattr(nested_field, 'json_api_link', False):
                    # If embed=field_name is appended to the query string or 'always_embed' flag is True, directly embed the
                    # results in addition to adding a relationship link
                    if embeds and (field.field_name in embeds or getattr(field, 'always_embed', None)):
                        if enable_esi:
                            try:
                                result = field.to_esi_representation(attribute, envelope=envelope)
                            except SkipField:
                                continue
                        else:
                            try:
                                # If a field has an empty representation, it should not be embedded.
                                result = self.context['embed'][field.field_name](obj)
                            except SkipField:
                                result = None

                        if result:
                            data['embeds'][field.field_name] = result
                        else:
                            data['embeds'][field.field_name] = {'error': 'This field is not embeddable.'}
                    try:
                        if not (is_anonymous and
                                    hasattr(field, 'view_name') and
                                        field.view_name in self.views_to_hide_if_anonymous):
                            data['relationships'][field.field_name] = representation
                    except SkipField:
                        continue
                elif field.field_name == 'id':
                    data['id'] = representation
                elif field.field_name == 'links':
                    data['links'] = representation
                else:
                    data['attributes'][field.field_name] = representation

        if not data['relationships']:
            del data['relationships']

        if not data['embeds']:
            del data['embeds']

        if context_envelope:
            ret[context_envelope] = data
            if is_anonymous:
                ret['meta'] = {'anonymous': True}
        else:
            ret = data
        return ret

    def get_absolute_url(self, obj):
        raise NotImplementedError()

    def get_absolute_html_url(self, obj):
        return utils.extend_querystring_if_key_exists(obj.absolute_url, self.context['request'], 'view_only')

    # overrides Serializer: Add HTML-sanitization similar to that used by APIv1 front-end views
    def is_valid(self, clean_html=True, **kwargs):
        """
        After validation, scrub HTML from validated_data prior to saving (for create and update views)

        Exclude 'type' and '_id' from validated_data.

        """
        ret = super(JSONAPISerializer, self).is_valid(**kwargs)

        if clean_html is True:
            self._validated_data = self.sanitize_data()

        self._validated_data.pop('type', None)
        self._validated_data.pop('target_type', None)

        if self.context['request'].method in utils.UPDATE_METHODS:
            self._validated_data.pop('_id', None)

        return ret

    def sanitize_data(self):
        return utils.rapply(self.validated_data, sanitize.strip_html)


class JSONAPIRelationshipSerializer(BaseAPISerializer):
    """Base Relationship serializer. Requires that a `type_` option is set on `class Meta`.
    Provides a simplified serialization of the relationship, allowing for simple update request
    bodies.
    """
    id = ser.CharField(required=False, allow_null=True)
    type = TypeField(required=False, allow_null=True)

    def to_representation(self, obj):
        meta = getattr(self, 'Meta', None)
        type_ = getattr(meta, 'type_', None)
        assert type_ is not None, 'Must define Meta.type_'
        relation_id_field = self.fields['id']
        attribute = relation_id_field.get_attribute(obj)
        relationship = relation_id_field.to_representation(attribute)

        data = {'type': type_, 'id': relationship} if relationship else None

        return data


def DevOnly(field):
    """Make a field only active in ``DEV_MODE``. ::

        experimental_field = DevMode(CharField(required=False))
    """
    return field if settings.DEV_MODE else None


class RestrictedDictSerializer(ser.Serializer):
    def to_representation(self, obj):
        data = {}
        fields = [field for field in self.fields.values() if not field.write_only]

        for field in fields:
            try:
                attribute = field.get_attribute(obj)
            except ser.SkipField:
                continue

            if attribute is None:
                # We skip `to_representation` for `None` values so that
                # fields do not have to explicitly deal with that case.
                data[field.field_name] = None
            else:
                data[field.field_name] = field.to_representation(attribute)
        return data


def relationship_diff(current_items, new_items):
    """
    To be used in POST and PUT/PATCH relationship requests, as, by JSON API specs,
    in update requests, the 'remove' items' relationships would be deleted, and the
    'add' would be added, while for create requests, only the 'add' would be added.

    :param current_items: The current items in the relationship
    :param new_items: The items passed in the request
    :return:
    """

    return {
        'add': {k: new_items[k] for k in (set(new_items.keys()) - set(current_items.keys()))},
        'remove': {k: current_items[k] for k in (set(current_items.keys()) - set(new_items.keys()))}
    }


class AddonAccountSerializer(JSONAPISerializer):
    id = ser.CharField(source='_id', read_only=True)
    provider = ser.CharField(read_only=True)
    profile_url = ser.CharField(required=False, read_only=True)
    display_name = ser.CharField(required=False, read_only=True)

    links = links = LinksField({
        'self': 'get_absolute_url',
    })

    class Meta:
        type_ = 'external_accounts'

    def get_absolute_url(self, obj):
        kwargs = self.context['request'].parser_context['kwargs']
        kwargs.update({'account_id': obj._id})
        return utils.absolute_reverse(
            'users:user-external_account-detail',
            kwargs=kwargs
        )
        return obj.get_absolute_url()


class LinkedNode(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)

    class Meta:
        type_ = 'linked_nodes'


class LinkedRegistration(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)

    class Meta:
        type_ = 'linked_registrations'


class LinkedNodesRelationshipSerializer(BaseAPISerializer):
    data = ser.ListField(child=LinkedNode())
    links = LinksField({'self': 'get_self_url',
                        'html': 'get_related_url'})

    def get_self_url(self, obj):
        return obj['self'].linked_nodes_self_url

    def get_related_url(self, obj):
        return obj['self'].linked_nodes_related_url

    class Meta:
        type_ = 'linked_nodes'

    def get_pointers_to_add_remove(self, pointers, new_pointers):
        diff = relationship_diff(
            current_items={pointer._id: pointer for pointer in pointers},
            new_items={val['_id']: val for val in new_pointers}
        )

        nodes_to_add = []
        for node_id in diff['add']:
            node = AbstractNode.load(node_id)
            if not node:
                raise exceptions.NotFound(detail='Node with id "{}" was not found'.format(node_id))
            nodes_to_add.append(node)

        return nodes_to_add, diff['remove'].values()

    def make_instance_obj(self, obj):
        # Convenience method to format instance based on view's get_object
        return {'data': [
            pointer for pointer in
            obj.linked_nodes.filter(is_deleted=False, type='osf.node')
        ], 'self': obj}

    def update(self, instance, validated_data):
        collection = instance['self']
        auth = utils.get_user_auth(self.context['request'])

        add, remove = self.get_pointers_to_add_remove(pointers=instance['data'], new_pointers=validated_data['data'])

        for pointer in remove:
            collection.rm_pointer(pointer, auth)
        for node in add:
            collection.add_pointer(node, auth)

        return self.make_instance_obj(collection)

    def create(self, validated_data):
        instance = self.context['view'].get_object()
        auth = utils.get_user_auth(self.context['request'])
        collection = instance['self']

        add, remove = self.get_pointers_to_add_remove(pointers=instance['data'], new_pointers=validated_data['data'])

        if not len(add):
            raise api_exceptions.RelationshipPostMakesNoChanges

        for node in add:
            collection.add_pointer(node, auth)

        return self.make_instance_obj(collection)


class LinkedRegistrationsRelationshipSerializer(BaseAPISerializer):
    data = ser.ListField(child=LinkedRegistration())
    links = LinksField({'self': 'get_self_url',
                        'html': 'get_related_url'})

    def get_self_url(self, obj):
        return obj['self'].linked_registrations_self_url

    def get_related_url(self, obj):
        return obj['self'].linked_registrations_related_url

    class Meta:
        type_ = 'linked_registrations'

    def get_pointers_to_add_remove(self, pointers, new_pointers):
        diff = relationship_diff(
            current_items={pointer._id: pointer for pointer in pointers},
            new_items={val['_id']: val for val in new_pointers}
        )

        nodes_to_add = []
        for node_id in diff['add']:
            node = AbstractNode.load(node_id)
            if not node:
                raise exceptions.NotFound(detail='Node with id "{}" was not found'.format(node_id))
            nodes_to_add.append(node)

        return nodes_to_add, diff['remove'].values()

    def make_instance_obj(self, obj):
        # Convenience method to format instance based on view's get_object
        return {'data': [
            pointer for pointer in
            obj.linked_nodes.filter(is_deleted=False, type='osf.registration')
        ], 'self': obj}

    def update(self, instance, validated_data):
        collection = instance['self']
        auth = utils.get_user_auth(self.context['request'])

        add, remove = self.get_pointers_to_add_remove(pointers=instance['data'], new_pointers=validated_data['data'])

        for pointer in remove:
            collection.rm_pointer(pointer, auth)
        for node in add:
            collection.add_pointer(node, auth)

        return self.make_instance_obj(collection)

    def create(self, validated_data):
        instance = self.context['view'].get_object()
        auth = utils.get_user_auth(self.context['request'])
        collection = instance['self']

        add, remove = self.get_pointers_to_add_remove(pointers=instance['data'], new_pointers=validated_data['data'])

        if not len(add):
            raise api_exceptions.RelationshipPostMakesNoChanges

        for node in add:
            collection.add_pointer(node, auth)

        return self.make_instance_obj(collection)


class MaintenanceStateSerializer(ser.ModelSerializer):

    class Meta:
        model = MaintenanceState
        fields = ('level', 'message', 'start', 'end')
