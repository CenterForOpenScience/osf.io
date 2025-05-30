import collections
import re
from urllib.parse import urlparse

from furl import furl
import waffle
from django.urls import resolve, reverse, NoReverseMatch
from django.core.exceptions import ImproperlyConfigured
from packaging.version import Version

from rest_framework import exceptions
from rest_framework import serializers as ser
from rest_framework.fields import SkipField
from rest_framework.fields import get_attribute as get_nested_attributes
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.reverse import reverse as drf_reverse

from api.base import utils
from api.base.exceptions import EnumFieldMemberError
from osf.metrics.utils import YearMonth
from osf.utils import permissions as osf_permissions
from osf.utils import sanitize
from osf.utils import functional
from api.base import exceptions as api_exceptions
from api.base.settings import BULK_SETTINGS
from framework.auth import core as auth_core
from osf.models import (
    AbstractNode,
    DraftRegistration,
    MaintenanceState,
    Preprint,
    Guid,
    BaseFileNode,
)
from website import settings
from website.project.model import has_anonymous_link
from api.base.versioning import KEBAB_CASE_VERSION, get_kebab_snake_case_field

from osf.models.validators import SwitchValidator


def get_meta_type(serializer_class, request):
    meta = getattr(serializer_class, 'Meta', None)
    if meta is None:
        return None
    resource_type = getattr(meta, 'type_', None)
    if resource_type is not None:
        return resource_type
    try:
        return meta.get_type(request)
    except AttributeError:
        return None


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
                'meta': rel_meta or {},
            },
        })

    if self_link:
        ret['links'].update({
            'self': {
                'href': self_link or {},
                'meta': self_meta or {},
            },
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
        super().__init__(**kwargs)
        self.field = getattr(field, 'child_relation', field)
        # source is intentionally field.source and not self.field.source
        self.source = field.source
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
        super().bind(field_name, parent)
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

    def __init__(self, field, min_version=None, max_version=None, **kwargs):
        super().__init__(field, **kwargs)
        self.min_version = min_version
        self.max_version = max_version
        self.help_text = f'This field is deprecated as of version {self.max_version}' or kwargs.get('help_text')

    def should_hide(self, instance):
        request = self.context.get('request')
        return request and utils.is_deprecated(request.version, self.min_version, self.max_version)


class ShowIfCurrentUser(ConditionalField):

    def should_show(self, instance):
        request = self.context.get('request')
        return request and request.user == instance


class ShowIfAdminScopeOrAnonymous(ConditionalField):

    def should_show(self, instance):
        request = self.context.get('request')
        has_admin_scope = instance.has_admin_scope if hasattr(instance, 'has_admin_scope') else utils.has_admin_scope(request)
        return request and (request.user.is_anonymous or has_admin_scope)


class ShowIfObjectPermission(ConditionalField):
    """Show the field only for users with a given object permission
    """
    def __init__(self, field, *, permission: str, **kwargs):
        super().__init__(field, **kwargs)
        self._required_object_permission = permission

    def should_show(self, instance):
        _request = self.context.get('request')
        return _request.user.has_perm(self._required_object_permission, obj=instance)


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


class HideIfPreprint(ConditionalField):
    """
    If object is a preprint or related to a preprint, hide the field.
    """

    def should_hide(self, instance):
        if getattr(instance, 'node', False) and isinstance(getattr(instance, 'node', False), Preprint):
            # Sometimes a "node" might be a preprint object where node/preprint code is shared
            return True

        return isinstance(instance, Preprint) \
            or isinstance(getattr(instance, 'target', None), Preprint) \
            or isinstance(getattr(instance, 'preprint', False), Preprint)

    def should_be_none(self, instance):
        return not isinstance(self.field, RelationshipField)


class HideIfDraftRegistration(ConditionalField):
    """
    If object is a draft registration, or related to a draft registration, hide the field.
    """

    def should_hide(self, instance):
        return isinstance(instance, DraftRegistration) \
            or isinstance(getattr(instance, 'draft_registration', False), DraftRegistration)

    def should_be_none(self, instance):
        return not isinstance(self.field, RelationshipField)


class NoneIfWithdrawal(ConditionalField):
    """
    If preprint is withdrawn, this field (attribute or relationship) should return None instead of hidden.
    """

    def should_hide(self, instance):
        return instance.is_retracted

    def should_be_none(self, instance):
        return True


class HideIfWithdrawal(ConditionalField):
    """
    If registration is withdrawn, this field will return None.
    """

    def should_hide(self, instance):
        return instance.is_retracted

    def should_be_none(self, instance):
        return not isinstance(self.field, RelationshipField)


class HideIfNotWithdrawal(ConditionalField):

    def should_hide(self, instance):
        return not instance.is_retracted


class HideIfWikiDisabled(ConditionalField):
    """
    If wiki is disabled, don't show relationship field, only available after 2.7
    """

    def should_hide(self, instance):
        request = self.context.get('request')
        has_wiki_addon = instance.has_wiki_addon if hasattr(instance, 'has_wiki_addon') else instance.has_addon('wiki')
        return not utils.is_deprecated(request.version, min_version='2.8') and not has_wiki_addon

class HideIfWithdrawalOrWikiDisabled(ConditionalField):
    """
    If wiki is disabled or registration is withdrawn, don't show relationship field, only available after 2.7
    """

    def should_hide(self, instance):
        request = self.context.get('request')
        has_wiki_addon = instance.has_wiki_addon if hasattr(instance, 'has_wiki_addon') else instance.has_addon('wiki')
        return instance.is_retracted or (not utils.is_deprecated(request.version, min_version='2.8') and not has_wiki_addon)

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
        super().__init__(**kwargs)
        self.field = field

    def to_representation(self, value):
        return self.field.to_representation(value)

    def bind(self, field_name, parent):
        super().bind(field_name, parent)
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
    elif isinstance(val, str):  # if a string is passed, it's a method of the serializer
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
            if Version(request.version) >= Version('2.2'):
                self.format = '%Y-%m-%dT%H:%M:%S.%fZ'
            else:
                self.format = '%Y-%m-%dT%H:%M:%S.%f' if value.microsecond else '%Y-%m-%dT%H:%M:%S'
        return super().to_representation(value)


class IDField(ser.CharField):
    """
    ID field that validates that 'id' in the request body is the same as the instance 'id' for single requests.
    """

    def __init__(self, **kwargs):
        kwargs['label'] = 'ID'
        super().__init__(**kwargs)

    # Overrides CharField
    def to_internal_value(self, data):
        request = self.context.get('request')
        if request:
            if request.method in utils.UPDATE_METHODS and not utils.is_bulk_request(request):
                id_field = self.get_id(self.root.instance)
                if id_field != data:
                    raise api_exceptions.Conflict(
                        detail=(
                            f'The id you used in the URL, "{id_field}", does not match the id you used in the json'
                            f' body\'s id field, "{data}". The object "{id_field}" exists, otherwise you\'d get a'
                            f' 404, so most likely you need to change the id field to match.'
                        ),
                    )
        return super().to_internal_value(data)

    def get_id(self, obj):
        return getattr(obj, self.source, '_id')


class GuidOrIDField(IDField):

    def get_id(self, obj):
        if isinstance(obj, BaseFileNode) and self.source == '_id':
            guid = Guid.load(self.context['view'].kwargs['file_id'])
            if guid:
                return guid._id

        return super().get_id(obj)


class TypeField(ser.CharField):
    """
    Type field that validates that 'type' in the request body is the same as the Meta type.

    Also ensures that type is write-only and required.
    """

    def __init__(self, **kwargs):
        kwargs['write_only'] = True
        kwargs['required'] = True
        super().__init__(**kwargs)

    # Overrides CharField
    def to_internal_value(self, data):
        request = self.context.get('request', None)
        if isinstance(self.root, JSONAPIListSerializer):
            type_ = get_meta_type(self.root.child, request)
        else:
            type_ = get_meta_type(self.root, request)
        kebab_case = str(type_).replace('-', '_')
        if type_ != data and kebab_case == data:
            type_ = kebab_case
            self.context['request'].META.setdefault('warning', 'As of API Version {0}, all types are now Kebab-case. {0} will accept snake_case, but this will be deprecated in future versions.'.format(KEBAB_CASE_VERSION))
        elif type_ != data:
            raise api_exceptions.Conflict(detail=(f'This resource has a type of "{type_}", but you set the json body\'s type field to "{data}". You probably need to change the type field to match the resource\'s type.'))
        return super().to_internal_value(data)


class TargetTypeField(ser.CharField):
    """
    Enforces that the related resource has the correct type
    """

    def __init__(self, **kwargs):
        kwargs['write_only'] = True
        kwargs['required'] = True
        self.target_type = kwargs.pop('target_type')
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if self.target_type != data:
            raise api_exceptions.Conflict(detail=(f'The target resource has a type of "{self.target_type}", but you set the json body\'s type field to "{data}".  You probably need to change the type field to match the target resource\'s type.'))
        return super().to_internal_value(data)


class JSONAPIListField(ser.ListField):
    def to_internal_value(self, data):
        if not isinstance(data, list):
            self.fail('not_a_list', input_type=type(data).__name__)

        return super().to_internal_value(data)


class ValuesListField(JSONAPIListField):
    """
    JSONAPIListField that uses a values_list with flat=True to return just
    an array of the specified field (attr_name) for optimization purposes.
    """
    def __init__(self, **kwargs):
        self.attr_name = kwargs.pop('attr_name')
        super().__init__(**kwargs)

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
        super().__init__(source=self.source, **kwargs)

    def get_attribute(self, obj):
        user = self.context['request'].user
        auth = auth_core.Auth(user)
        field_source_method = getattr(obj, self.source)
        return field_source_method(auth=auth)

class AnonymizedRegexField(AuthorizedCharField):
    r"""
    Performs a regex replace on the content of the authorized object's
    source field when an anonymous view is requested.

    Example:
        content = AnonymizedRegexField(source='get_content', regex='\[@[^\]]*\]\([^\) ]*\)', replace='@A User')
    """

    def __init__(self, source, regex, replace, **kwargs):
        self.source = source
        self.regex = regex
        self.replace = replace
        super().__init__(source=self.source, **kwargs)

    def get_attribute(self, obj):
        value = super().get_attribute(obj)

        if value:
            user = self.context['request'].user
            auth = auth_core.Auth(user)
            if 'view_only' in self.context['request'].query_params:
                auth.private_key = self.context['request'].query_params['view_only']
                if has_anonymous_link(obj.node, auth):
                    value = re.sub(self.regex, self.replace, value)

        return value

class RelationshipField(ser.Field):
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
    field is assumed to be a method on the serializer. ::

        root = RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<root._id>'}
        )

        region = RegionRelationshipField(
            related_view='regions:region-detail',
            related_view_kwargs={'region_id': 'get_region_id'},
            read_only=False
        )

    'root._id' is enclosed in angular brackets, but 'get_region_id' is not.
    'root._id' will be looked up on the target, but 'get_region_id' will be executed on the serializer.

    Field can handle a filter_key, which is a django field lookup used by
    `api.base.filters.FilterMixin` to filter a QuerySet for requests to a
    list view with a `filter[field_name]=foo` query param. An alternative
    to adding more noise to the various `postprocess_query_param` methods

    Field can include optional filters:

    Example:
    replies = RelationshipField(
        self_view='nodes:node-comments',
        self_view_kwargs={'node_id': '<node._id>'},
        filter={'target': '<_id>'})
    )
    """
    json_api_link = True  # serializes to a links object

    def __init__(
        self, *,
        related_view=None, related_view_kwargs=None, related_meta=None,
        self_view=None, self_view_kwargs=None, self_meta=None,
        filter=None, always_embed=False, filter_key=None,
        # ser.Field params with altered defaults:
        required=False, read_only=True,
        **kwargs,
    ):
        self.views = {'related': related_view, 'self': self_view}
        self.view_kwargs = {'related': related_view_kwargs, 'self': self_view_kwargs}
        self.related_meta = related_meta
        self.self_meta = self_meta
        self.filter = filter
        self.always_embed = always_embed
        self.filter_key = filter_key

        if related_view:
            assert related_view_kwargs is not None, 'Must provide related view kwargs.'
            if not callable(related_view_kwargs):
                assert isinstance(
                    related_view_kwargs,
                    dict,
                ), "Related view kwargs must have format {'lookup_url_kwarg: lookup_field}."
        if self_view:
            assert self_view_kwargs is not None, 'Must provide self view kwargs.'
            assert isinstance(self_view_kwargs, dict), "Self view kwargs must have format {'lookup_url_kwarg: lookup_field}."
        self.view_name = related_view or self_view
        assert self.view_name is not None, 'self_view or related_view must be specified.'
        self.lookup_url_kwarg = (
            related_view_kwargs
            if related_view
            else self_view_kwargs
        )
        super().__init__(required=required, read_only=read_only, **kwargs)

    def get_attribute(self, instance):
        return instance

    def resolve(self, resource, field_name, request):
        """
        Resolves the view when embedding.
        """
        lookup_url_kwarg = self.lookup_url_kwarg
        if callable(lookup_url_kwarg):
            lookup_url_kwarg = lookup_url_kwarg(self.get_attribute(resource))

        kwargs = {attr_name: self.lookup_attribute(resource, attr) for (attr_name, attr) in lookup_url_kwarg.items()}
        kwargs.update({'version': request.parser_context['kwargs']['version']})

        view = self.view_name
        if callable(view):
            view = self._handle_callable_view(resource, view)
        try:
            view_url = reverse(view, kwargs=kwargs)
        except NoReverseMatch as e:
            # Handle private endpoint view serialization when it is a relationship in a public one
            if kwargs.get('version', False):
                kwargs.pop('version')
                view_url = drf_reverse(view, kwargs=kwargs)
            else:
                raise e
        return resolve(view_url)

    def process_related_counts_parameters(self, params, value):
        """
        Processes related_counts parameter.

        Can either be a True/False value for fetching counts on all fields, or a comma-separated list for specifying
        individual fields.  Ensures field for which we are requesting counts is a relationship field.
        """
        if utils.is_truthy(params) or utils.is_falsy(params):
            return params

        field_counts_requested = [val for val in params.split(',')]

        countable_fields = {
            field for field in self.parent.fields if
            getattr(self.parent.fields[field], 'json_api_link', False) or
            getattr(getattr(self.parent.fields[field], 'field', None), 'json_api_link', None)
        }
        for count_field in field_counts_requested:
            # Some fields will hide relationships, e.g. HideIfWithdrawal
            # Ignore related_counts for these fields
            fetched_field = self.parent.fields.get(count_field)

            hidden = fetched_field and isinstance(fetched_field, HideIfWithdrawal) and getattr(value, 'is_retracted', False)

            if not hidden and count_field not in countable_fields:
                raise api_exceptions.InvalidQueryStringError(
                    detail="Acceptable values for the related_counts query param are 'true', 'false', or any of the relationship fields; got '{}'".format(
                        params,
                    ),
                    parameter='related_counts',
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
                    meta[key] = functional.rapply(meta_data[key], _url_val, obj=value, serializer=self.parent, request=self.context['request'])
                elif utils.is_falsy(show_related_counts):
                    continue
                elif self.field_name in field_counts_requested:
                    meta[key] = functional.rapply(meta_data[key], _url_val, obj=value, serializer=self.parent, request=self.context['request'])
                else:
                    continue
            elif key == 'projects_in_common':
                if not utils.get_user_auth(self.context['request']).user:
                    continue
                if not self.context['request'].query_params.get('show_projects_in_common', False):
                    continue
                meta[key] = functional.rapply(meta_data[key], _url_val, obj=value, serializer=self.parent, request=self.context['request'])
            else:
                meta[key] = functional.rapply(meta_data[key], _url_val, obj=value, serializer=self.parent, request=self.context['request'])
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
            except (KeyError, AttributeError):
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

            if _tpl(lookup_field):
                lookup_value = self.lookup_attribute(obj, lookup_field)
            else:
                lookup_value = _url_val(lookup_field, obj, self.parent, self.context['request'])

            if lookup_value is None:
                return None
            kwargs_retrieval[lookup_url_kwarg] = lookup_value
        return kwargs_retrieval

    def _handle_callable_view(self, obj, view):
        return view(self.get_attribute(obj))

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
                        view = self._handle_callable_view(obj, view)
                    if request.parser_context['kwargs'].get('version', False):
                        kwargs.update({'version': request.parser_context['kwargs']['version']})
                    try:
                        url = drf_reverse(view, kwargs=kwargs, request=request, format=format)
                    except NoReverseMatch as e:
                        # Handle private endpoint view serialization when it is a relationship in a public one
                        if kwargs.get('version', False):
                            kwargs.pop('version')
                            url = utils.absolute_reverse(view, kwargs=kwargs)
                        else:
                            raise e

                    if self.filter:
                        formatted_filters = self.format_filter(obj)
                        if formatted_filters:
                            for filter in formatted_filters:
                                url = utils.extend_querystring_params(
                                    url,
                                    {'filter[{}]'.format(filter['field_name']): filter['value']},
                                )
                        else:
                            url = None

                    if url:
                        url = utils.extend_querystring_if_key_exists(
                            url, self.context['request'],
                            'view_only',
                        )
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
                query_dict = dict(format=['jsonapi'], envelope=[envelope])
                if 'view_only' in self.parent.context['request'].query_params.keys():
                    query_dict.update(view_only=[self.parent.context['request'].query_params['view_only']])
                esi_url = utils.extend_querystring_params(href, query_dict)
                return f'<esi:include src="{esi_url}"/>'

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

    # Overrides Field
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
        # Eg. Consider a RelationshipField pointing from a json
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
            # Prior to 2.9, empty relationships were omitted from the response.
            # This conflicts with the JSON-API spec and was fixed in 2.9.
            if Version(request.version) < Version('2.9'):
                raise SkipField
            else:
                return {'data': None}

        related_url = url['related']
        related_path = urlparse(related_url).path if related_url else None
        related_meta = self.get_meta_information(self.related_meta, value)
        self_url = url['self']
        self_meta = self.get_meta_information(self.self_meta, value)
        relationship = format_relationship_links(related_url, self_url, related_meta, self_meta)
        if related_url:
            resolved_url = resolve(related_path)
            related_class = resolved_url.func.view_class
            if issubclass(related_class, RetrieveModelMixin):
                try:
                    related_type = resolved_url.namespace.split(':')[-1]
                    # TODO: change kwargs to preprint_provider_id and registration_id
                    if related_class.view_name == 'node-settings':
                        related_id = resolved_url.kwargs['node_id']
                        related_type = 'node-setting'
                    elif related_class.view_name == 'node-storage':
                        related_id = resolved_url.kwargs['node_id']
                        related_type = 'node-storage'
                    elif related_class.view_name == 'node-citation' \
                            or related_class.view_name == 'registration-citation':
                        related_id = resolved_url.kwargs['node_id']
                        related_type = 'citation'
                    elif related_class.view_name == 'preprint-citation':
                        related_id = resolved_url.kwargs['preprint_id']
                        related_type = 'citation'
                    elif related_type in ('preprint_providers', 'preprint-providers', 'registration-providers'):
                        related_id = resolved_url.kwargs['provider_id']
                    elif related_type in ('registrations', 'draft_nodes'):
                        related_id = resolved_url.kwargs['node_id']
                    elif related_type == 'schemas' and related_class.view_name == 'registration-schema-detail':
                        related_id = resolved_url.kwargs['schema_id']
                        related_type = 'registration-schemas'
                    elif related_type == 'users' and related_class.view_name == 'user_settings':
                        related_id = resolved_url.kwargs['user_id']
                        related_type = 'user-settings'
                    elif related_type == 'institutions' and related_class.view_name == 'institution-summary-metrics':
                        related_id = resolved_url.kwargs['institution_id']
                        related_type = 'institution-summary-metrics'
                    elif related_type == 'collections' and related_class.view_name == 'collection-submission-detail':
                        related_id = f'{resolved_url.kwargs['collection_submission_id']}-{resolved_url.kwargs['collection_id']}'
                        related_type = 'collection-submission'
                    elif related_type == 'collection-providers' and related_class.view_name == 'collection-provider-detail':
                        related_id = resolved_url.kwargs['provider_id']
                        related_type = 'collection-providers'
                    elif related_type == 'registration-providers' and related_class.view_name == 'registration-provider-detail':
                        related_id = resolved_url.kwargs['provider_id']
                        related_type = 'registration-providers'
                    elif related_type == 'preprint-providers' and related_class.view_name == 'preprint-provider-detail':
                        related_id = resolved_url.kwargs['provider_id']
                        related_type = 'preprint-providers'
                    elif related_type == 'custom-item-metadata':
                        related_id = resolved_url.kwargs['guid_id']
                        related_type = 'custom-item-metadata-records'
                    elif related_type == 'custom-file-metadata':
                        related_id = resolved_url.kwargs['guid_id']
                        related_type = 'custom-file-metadata-records'
                    elif related_type == 'cedar-metadata-templates' and related_class.view_name == 'cedar-metadata-template-detail':
                        related_id = resolved_url.kwargs['template_id']
                    else:
                        related_id = resolved_url.kwargs[related_type[:-1] + '_id']
                except KeyError:
                    return relationship
                relationship['data'] = {'id': related_id, 'type': related_type}
        return relationship


class TypedRelationshipField(RelationshipField):
    """ Overrides get_url to inject a typed namespace.

        Assumption: Namespaces for each type MUST be the same as the dasharized JSONAPI-type
    """

    def get_url(self, obj, view_name, request, format):
        if len(view_name.split(':')) == 2:
            untyped_view = view_name
            view_parts = view_name.split(':')
            request = self.context.get('request', None)
            if isinstance(self.root, JSONAPIListSerializer):
                view_parts.insert(1, get_meta_type(self.root.child, request).replace('_', '-'))
            else:
                view_parts.insert(1, get_meta_type(self.root, request).replace('_', '-'))
            self.view_name = view_name = ':'.join(view_parts)
            for k, v in list(self.views.items()):
                if v == untyped_view:
                    self.views[k] = view_name
        return super().get_url(obj, view_name, request, format)


class FileRelationshipField(RelationshipField):
    def get_url(self, obj, view_name, request, format):
        if obj.kind == 'folder':
            raise SkipField
        return super().get_url(obj, view_name, request, format)


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
            'lookup_kwarg': 'node_id',
        },
        'registration': {
            'view': 'registrations:registration-detail',
            'lookup_kwarg': 'node_id',
        },
        'preprint': {
            'view': 'preprints:preprint-detail',
            'lookup_kwarg': 'preprint_id',
        },
        'draft-node': {
            'view': 'draft_nodes:node-detail',
            'lookup_kwarg': 'node_id',
        },
        'comment': {
            'view': 'comments:comment-detail',
            'lookup_kwarg': 'comment_id',
        },
        'nodewikipage': {
            'view': None,
            'lookup_kwarg': None,
        },
    }

    def __init__(self, **kwargs):
        self.meta = kwargs.pop('meta', {})
        self.link_type = kwargs.pop('link_type', 'url')
        super().__init__(read_only=True, **kwargs)

    def resolve(self, resource, field_name, request):
        """
        Resolves the view for target node or target comment when embedding.
        """
        if hasattr(resource.target, 'referent'):
            name = resource.target.referent._name
        else:
            name = resource.target.__class__.__name__.lower()

        view_info = self.view_map.get(name, None)
        if not view_info:
            raise api_exceptions.TargetNotSupportedError(f'{name} is not a supported target type')

        if not view_info['view']:
            return None, None, None
        embed_value = resource.target._id

        return resolve(
            reverse(
                view_info['view'],
                kwargs={
                    view_info['lookup_kwarg']: embed_value,
                    'version': request.parser_context['kwargs']['version'],
                },
            ),
        )

    def to_esi_representation(self, value, envelope='data'):
        href = value.get_absolute_url()

        if href:
            esi_url = utils.extend_querystring_params(href, dict(envelope=[envelope], format=['jsonapi']))
            return f'<esi:include src="{esi_url}"/>'
        return self.to_representation(value)

    def to_representation(self, value):
        """
        Returns nested dictionary in format {'links': {'self.link_type': ... }

        If no meta information, self.link_type is equal to a string containing link's URL.  Otherwise,
        the link is represented as a links object with 'href' and 'meta' members.
        """
        meta = functional.rapply(self.meta, _url_val, obj=value, serializer=self.parent, request=self.context['request'])
        obj = getattr(value, 'referent', value)
        return {
            'links': {
                self.link_type: {
                    'href': obj.get_absolute_url(),
                    'meta': meta,
                },
            },
            'data': {
                'type': meta['type'],
                'id': obj._id,
            },
        }


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

    def _extend_url_with_vol_key(self, url):
        return utils.extend_querystring_if_key_exists(url, self.context['request'], 'view_only')

    def to_representation(self, obj):
        ret = {}
        for name, value in self.links.items():
            try:
                url = _url_val(value, obj=obj, serializer=self.parent, request=self.context['request'])
            except SkipField:
                continue

            if name in ['self', 'info']:
                ret[name] = self._extend_url_with_vol_key(url)
            else:
                ret[name] = url

        if 'self' not in ret and hasattr(obj, 'get_absolute_url'):
            ret['self'] = self._extend_url_with_vol_key(obj.get_absolute_url())

        if 'iri' not in ret:
            try:
                ret['iri'] = obj.get_semantic_iri()
            except (AttributeError, ValueError):
                pass

        if 'info' in ret:
            if hasattr(obj, 'get_absolute_info_url'):
                ret['info'] = self._extend_url_with_vol_key(obj.get_absolute_info_url())

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
                ),
            )
    else:
        return attr_tpl


# TODO: Make this a Field that is usable on its own?
class Link:
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
            **self.reverse_kwargs,
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

        base_url = None
        if hasattr(obj.target, 'osfstorage_region'):
            base_url = obj.target.osfstorage_region.waterbutler_url

        url = utils.waterbutler_api_url_for(obj.target._id, obj.provider, obj.path, base_url=base_url, **self.kwargs)
        if not url:
            raise SkipField
        else:
            return url


class RelatedLambdaRelationshipField(RelationshipField):
    """
    An extension of a RelationshipField which enables the use of a lambda
    function to determine the related_view where the argument of the lambda
    function is an attribute, distinct from the field name, on the serialized object.

    e.g. (NodeFileHyperLinkField extends this class)
    files = NodeFileHyperLinkField(
        related_view=lambda node: 'draft_nodes:node-files' if getattr(node, 'type', False) == 'osf.draftnode' else 'nodes:node-files',
        view_lambda_argument='target',
        related_view_kwargs={'node_id': '<target._id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder',
    )
    In a standard RelationshipField, the lambda for the related_view would fail to evaluate because
    the argument would be <serialized_object>.files while the lambda's argument should be <serialized_object.target>.
    This class uses the `view_lambda_argument` to determine the attribute on the serialized object to use
    as the argument for the lambda function.
    """

    def __init__(self, view_lambda_argument=None, **kws):
        self.view_lambda_argument = view_lambda_argument
        super().__init__(**kws)

    def _handle_callable_view(self, obj, view):
        return view(getattr(obj, self.view_lambda_argument))


class NodeFileHyperLinkField(RelatedLambdaRelationshipField):
    def __init__(self, kind=None, never_embed=False, **kws):
        self.kind = kind
        self.never_embed = never_embed
        super().__init__(**kws)

    def get_url(self, obj, view_name, request, format):
        if self.kind and obj.kind != self.kind:
            raise SkipField
        return super().get_url(obj, view_name, request, format)


class JSONAPIListSerializer(ser.ListSerializer):
    def to_representation(self, data):
        enable_esi = self.context.get('enable_esi', False)
        envelope = self.context.update({'envelope': None})
        # Don't envelope when serializing collection
        errors = {}
        bulk_skip_uneditable = utils.is_truthy(self.context['request'].query_params.get('skip_uneditable', False))

        if isinstance(data, collections.abc.Mapping):
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
        from api.nodes.serializers import CompoundIDField

        # if PATCH request, the child serializer's partial attribute needs to be True
        if self.context['request'].method == 'PATCH':
            self.child.partial = True

        bulk_skip_uneditable = utils.is_truthy(self.context['request'].query_params.get('skip_uneditable', False))
        if not bulk_skip_uneditable:
            if len(instance) != len(validated_data):
                raise exceptions.ValidationError({'non_field_errors': 'Could not find all objects to update.'})

        id_lookup = self.child.fields['id'].source
        data_mapping = {item.get(id_lookup): item for item in validated_data}

        if isinstance(self.child.fields['id'], CompoundIDField):
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
            raise api_exceptions.JSONAPIException(
                source={'pointer': '/data'},
                detail=f'Bulk operation limit is {bulk_limit}, got {num_items}.',
            )

        return super().run_validation(data)

    # overrides ListSerializer: Add HTML-sanitization similar to that used by APIv1 front-end views
    def is_valid(self, clean_html=True, **kwargs):
        """
        After validation, scrub HTML from validated_data prior to saving (for create and update views)

        Exclude 'type' from validated_data.

        """
        ret = super().is_valid(**kwargs)

        if clean_html is True:
            self._validated_data = functional.rapply(self.validated_data, sanitize.strip_html)

        for data in self._validated_data:
            data.pop('type', None)

        return ret


class BaseAPISerializer(ser.Serializer):
    def parse_sparse_fields(self):
        request = self.context.get('request')
        if request:
            sparse_fieldset_query_param = f'fields[{get_meta_type(self, request)}]'
            if sparse_fieldset_query_param in request.query_params:
                fieldset = request.query_params[sparse_fieldset_query_param].split(',')
                for field_name in list(self.fields.keys()):
                    if field_name in ('id', 'links', 'type'):
                        # MUST return these fields
                        continue
                    if field_name not in fieldset:
                        self.fields.pop(field_name)


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
        invalid_embeds = set(embeds.keys()) - {
            f.field_name for f in fields_check if getattr(f, 'json_api_link', False)
        }
        return invalid_embeds

    def to_esi_representation(self, data, envelope='data'):
        query_params_blacklist = ['page[size]']
        href = self.get_absolute_url(data)
        if href and href != '{}':
            # NOTE: furl encoding to be verified later
            esi_url = furl(href).add(args=dict(self.context['request'].query_params)).remove(
                args=query_params_blacklist,
            ).remove(args=['envelope']).add(args={'envelope': envelope}).url
            return f'<esi:include src="{esi_url}"/>'
        # failsafe, let python do it if something bad happened in the ESI construction
        return super().to_representation(data)

    def run_validation(self, data):
        # Overrides construtor for validated_data to allow writes to a SerializerMethodField
        # Validation for writeable SMFs is expected to happen in the model
        _validated_data = super().run_validation(data)
        for field in self.writeable_method_fields:
            if field in data:
                _validated_data[field] = data[field]
        return _validated_data

    # overrides Serializer
    def to_representation(self, obj, envelope='data'):
        """Serialize to final representation.

        :param obj: Object to be serialized.
        :param envelope: Key for resource object.
        """
        ret = {}
        request = self.context.get('request')
        type_ = get_meta_type(self, request)
        assert type_ is not None, 'Must define Meta.type_ or Meta.get_type()'
        self.parse_sparse_fields()

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

        fields = [
            field for field in self.fields.values() if
            not field.write_only and field.field_name not in to_be_removed
        ]

        invalid_embeds = self.invalid_embeds(fields, embeds)
        invalid_embeds = invalid_embeds - to_be_removed
        if invalid_embeds:
            raise api_exceptions.InvalidQueryStringError(
                parameter='embed',
                detail='The following fields are not embeddable: {}'.format(
                    ', '.join(invalid_embeds),
                ),
            )

        for field in fields:
            nested_field = utils.decompose_field(field)
            try:
                attribute = field.get_attribute(obj)
            except SkipField:
                continue
            if attribute is None:
                # We skip `to_representation` for `None` values so that
                # fields do not have to explicitly deal with that case.
                if isinstance(nested_field, RelationshipField):
                    # if this is a RelationshipField, serialize as a null relationship
                    data['relationships'][field.field_name] = {'data': None}
                else:
                    # otherwise, serialize as an null attribute
                    data['attributes'][field.field_name] = None
            else:
                try:
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
                        if not (
                            is_anonymous and
                            hasattr(field, 'view_name') and
                                field.view_name in self.views_to_hide_if_anonymous
                        ):
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

        additional_meta = self.get_meta(obj)
        if additional_meta:
            meta_obj = ret.setdefault('meta', {})
            meta_obj.update(additional_meta)
        return ret

    def get_absolute_url(self, obj):
        raise NotImplementedError()

    def get_meta(self, obj):
        return None

    def get_absolute_html_url(self, obj):
        return utils.extend_querystring_if_key_exists(obj.absolute_url, self.context['request'], 'view_only')

    # overrides Serializer: Add HTML-sanitization similar to that used by APIv1 front-end views
    def is_valid(self, clean_html=True, **kwargs):
        """
        After validation, scrub HTML from validated_data prior to saving (for create and update views)

        Exclude 'type' and '_id' from validated_data.

        """
        try:
            ret = super().is_valid(**kwargs)
        except exceptions.ValidationError as e:

            # The following is for special error handling for ListFields.
            # Without the following, the error detail on the API response would be
            # a list instead of a string.
            for key in e.detail.keys():
                if isinstance(e.detail[key], dict):
                    e.detail[key] = next(iter(e.detail[key].values()))
            raise e

        if clean_html is True:
            self._validated_data = self.sanitize_data()

        self._validated_data.pop('type', None)
        self._validated_data.pop('target_type', None)

        if self.context['request'].method in utils.UPDATE_METHODS:
            self._validated_data.pop('_id', None)

        return ret

    def sanitize_data(self):
        return functional.rapply(self.validated_data, sanitize.strip_html)


class JSONAPIRelationshipSerializer(BaseAPISerializer):
    """Base Relationship serializer. Requires that a `type_` option is set on `class Meta`.
    Provides a simplified serialization of the relationship, allowing for simple update request
    bodies.
    """
    id = ser.CharField(required=False, allow_null=True)
    type = TypeField(required=False, allow_null=True)

    def to_representation(self, obj):
        request = self.context.get('request')
        type_ = get_meta_type(self, request)
        assert type_ is not None, 'Must define Meta.type_ or Meta.get_type()'
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
        'remove': {k: current_items[k] for k in (set(current_items.keys()) - set(new_items.keys()))},
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
        @staticmethod
        def get_type(request):
            return get_kebab_snake_case_field(request.version, 'external-accounts')

    def get_absolute_url(self, obj):
        kwargs = self.context['request'].parser_context['kwargs']
        kwargs.update({'account_id': obj._id})
        return utils.absolute_reverse(
            'users:user-external_account-detail',
            kwargs=kwargs,
        )
        return obj.get_absolute_url()


class LinkedNode(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)

    class Meta:
        @staticmethod
        def get_type(request):
            if Version(request.version) < Version('2.13'):
                return 'linked_nodes'
            return 'nodes'


class LinkedRegistration(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)

    class Meta:
        @staticmethod
        def get_type(request):
            if Version(request.version) < Version('2.13'):
                return 'linked_registrations'
            return 'registrations'


class LinkedPreprint(LinkedNode):
    class Meta:
        @staticmethod
        def get_type(request):
            if Version(request.version) < Version('2.13'):
                return 'linked_preprints'
            return 'preprints'


class LinkedNodesRelationshipSerializer(BaseAPISerializer):
    data = ser.ListField(child=LinkedNode())
    links = LinksField({
        'self': 'get_self_url',
        'html': 'get_related_url',
    })

    def get_self_url(self, obj):
        return obj['self'].linked_nodes_self_url

    def get_related_url(self, obj):
        return obj['self'].linked_nodes_related_url

    class Meta:
        @staticmethod
        def get_type(request):
            if Version(request.version) < Version('2.13'):
                return 'linked_nodes'
            return 'nodes'

    def get_pointers_to_add_remove(self, pointers, new_pointers):
        diff = relationship_diff(
            current_items={pointer._id: pointer for pointer in pointers},
            new_items={val['_id']: val for val in new_pointers},
        )

        nodes_to_add = []
        for node_id in diff['add']:
            node = AbstractNode.load(node_id) or Preprint.load(node_id)
            if not node:
                raise exceptions.NotFound(detail=f'Node with id "{node_id}" was not found')
            nodes_to_add.append(node)

        return nodes_to_add, diff['remove'].values()

    def make_instance_obj(self, obj):
        # Convenience method to format instance based on view's get_object
        return {
            'data': [
                pointer for pointer in
                obj.linked_nodes.filter(is_deleted=False, type='osf.node')
            ], 'self': obj,
        }

    def update(self, instance, validated_data):
        collection = instance['self']
        auth = utils.get_user_auth(self.context['request'])

        add, remove = self.get_pointers_to_add_remove(pointers=instance['data'], new_pointers=validated_data['data'])

        for pointer in remove:
            collection.rm_pointer(pointer, auth)
        for node in add:
            try:
                collection.add_pointer(node, auth)
            except ValueError as e:
                raise api_exceptions.InvalidModelValueError(
                    detail=str(e),
                )

        return self.make_instance_obj(collection)

    def create(self, validated_data):
        instance = self.context['view'].get_object()
        auth = utils.get_user_auth(self.context['request'])
        collection = instance['self']

        add, remove = self.get_pointers_to_add_remove(pointers=instance['data'], new_pointers=validated_data['data'])

        if not len(add):
            raise api_exceptions.RelationshipPostMakesNoChanges

        for node in add:
            try:
                collection.add_pointer(node, auth)
            except ValueError as e:
                raise api_exceptions.InvalidModelValueError(
                    detail=str(e),
                )
        return self.make_instance_obj(collection)


class LinkedRegistrationsRelationshipSerializer(BaseAPISerializer):
    data = ser.ListField(child=LinkedRegistration())
    links = LinksField({
        'self': 'get_self_url',
        'html': 'get_related_url',
    })

    def get_self_url(self, obj):
        return obj['self'].linked_registrations_self_url

    def get_related_url(self, obj):
        return obj['self'].linked_registrations_related_url

    class Meta:
        @staticmethod
        def get_type(request):
            if Version(request.version) < Version('2.13'):
                return 'linked_registrations'
            return 'registrations'

    def get_pointers_to_add_remove(self, pointers, new_pointers):
        diff = relationship_diff(
            current_items={pointer._id: pointer for pointer in pointers},
            new_items={val['_id']: val for val in new_pointers},
        )

        nodes_to_add = []
        for node_id in diff['add']:
            node = AbstractNode.load(node_id)
            if not node:
                raise exceptions.NotFound(detail=f'Node with id "{node_id}" was not found')
            nodes_to_add.append(node)

        return nodes_to_add, diff['remove'].values()

    def make_instance_obj(self, obj):
        # Convenience method to format instance based on view's get_object
        return {
            'data': [
                pointer for pointer in
                obj.linked_nodes.filter(is_deleted=False, type='osf.registration')
            ], 'self': obj,
        }

    def update(self, instance, validated_data):
        collection = instance['self']
        auth = utils.get_user_auth(self.context['request'])

        add, remove = self.get_pointers_to_add_remove(pointers=instance['data'], new_pointers=validated_data['data'])

        for pointer in remove:
            collection.rm_pointer(pointer, auth)
        for node in add:
            try:
                collection.add_pointer(node, auth)
            except ValueError as e:
                raise api_exceptions.InvalidModelValueError(
                    detail=str(e),
                )

        return self.make_instance_obj(collection)

    def create(self, validated_data):
        instance = self.context['view'].get_object()
        auth = utils.get_user_auth(self.context['request'])
        collection = instance['self']

        add, remove = self.get_pointers_to_add_remove(pointers=instance['data'], new_pointers=validated_data['data'])

        if not len(add):
            raise api_exceptions.RelationshipPostMakesNoChanges

        for node in add:
            try:
                collection.add_pointer(node, auth)
            except ValueError as e:
                raise api_exceptions.InvalidModelValueError(
                    detail=str(e),
                )

        return self.make_instance_obj(collection)


class LinkedPreprintsRelationshipSerializer(LinkedNodesRelationshipSerializer):
    data = ser.ListField(child=LinkedPreprint())

    def get_self_url(self, obj):
        return obj['self'].linked_preprints_self_url

    def get_related_url(self, obj):
        return obj['self'].linked_preprints_related_url

    class Meta:
        @staticmethod
        def get_type(request):
            if Version(request.version) < Version('2.13'):
                return 'linked_preprints'
            return 'preprints'

    def make_instance_obj(self, obj):
        # Convenience method to format instance based on view's get_object
        return {
            'data': [
                pointer for pointer in
                obj.linked_nodes.filter(deleted__isnull=True, type='osf.preprint')
            ], 'self': obj,
        }


class MaintenanceStateSerializer(ser.ModelSerializer):

    class Meta:
        model = MaintenanceState
        fields = ('level', 'message', 'start', 'end')


class HideIfSwitch(ConditionalField):
    """
    If switch is switched this field is hidden/unhidden. This field is hidden if the switch state matches
    the value of the hide_if parameter.
    """
    def __init__(self, switch_name: str, field: ser.Field, hide_if: bool = False, **kwargs):
        """
        :param switch_name: The name of the switch that is validated
        :param field: The field that's being validated by the switch.
        :param hide_if: The value of the switch that indicates it's hidden.
        :param kwargs: You know, kwargs...
        """
        super().__init__(field, **kwargs)
        self.switch_name = switch_name
        self.hide_if = hide_if

    def should_hide(self, instance):
        return waffle.switch_is_active(self.switch_name) == self.hide_if


class DisableIfSwitch(HideIfSwitch):
    """
    If switch is switched this field will become hidden/unhidden and attempts to modify this field
    will result in a validation error/pass normally. This field is disabled if the switch state matches
    the value of the hide_if parameter.
    """
    def __init__(self, switch_name: str, field: ser.Field, hide_if: bool = False, **kwargs):
        """
        :param switch_name: The name of the switch that is validated
        :param field: The field that's being validated by the switch.
        :param hide_if: The value of the switch that indicates it's hidden/validated.
        :param kwargs: My mama always told me life is like a bunch of kwargs...
        """
        super().__init__(switch_name, field, hide_if, **kwargs)
        self.validators.append(SwitchValidator(self.switch_name))


class EnumField(ser.ChoiceField):
    """
    Custom field for using Int enums internally in a human-readable way.
    """
    def __init__(self, enum_class, **kwargs):
        self._enum_class = enum_class
        # We usually define this on the Enum class
        choices = tuple((entry.value, entry.name.lower()) for entry in enum_class)
        super().__init__(choices=choices, **kwargs)

    def to_representation(self, value):
        return self._enum_class(value).name.lower()

    def to_internal_value(self, data):
        try:
            return self._enum_class[data.upper()].value
        except KeyError:
            raise EnumFieldMemberError(self._enum_class, data)


class YearmonthField(ser.Field):
    def to_representation(self, value: YearMonth | None) -> str | None:
        if value is None:
            return None
        return str(value)

    def to_internal_value(self, data: str | None) -> YearMonth | None:
        if data is None:
            return None
        try:
            return YearMonth.from_str(data)
        except ValueError as e:
            raise ser.ValidationError(str(e))
