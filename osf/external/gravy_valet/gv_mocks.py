import contextlib
import itertools
import json
import typing
import re
import urllib.parse

import dataclasses  # backport
import responses

from . import auth_helpers
from osf.models import OSFUser, AbstractNode
from osf.utils import permissions as osf_permissions
from website import settings


@dataclasses.dataclass
class _MockGVEntity:

    RESOURCE_TYPE: typing.ClassVar[str]
    pk: int

    @property
    def api_path(self):
        return f'v1/{self.RESOURCE_TYPE}/{self.pk}/'

    def serialize(self):
        data = {
            'type': self.RESOURCE_TYPE,
            'id': self.pk,
            'attributes': self._serialize_attributes(),
            'links': self._serialize_links(),
        }
        relationships = self._serialize_relationships()
        if relationships:
            data['relationships'] = relationships
        return data

    def _serialize_attributes(self):
        ...

    def _serialize_relationships(self):
        ...

    def _serialize_links(self):
        return {'self': f'{settings.GRAVYVALET_URL}/{self.api_path}'}

    def _format_relationship_entry(self, relationship_path, related_type=None, related_pk=None):
        relationship_api_path = f'{settings.GRAVYVALET_URL}/{self.api_path}{relationship_path}/'
        relationship_entry = {'links': {'related': relationship_api_path}}
        if related_type and related_pk:
            relationship_entry['data'] = {'type': related_type, 'id': related_pk}
        return relationship_entry

@dataclasses.dataclass
class _MockUserReference(_MockGVEntity):

    RESOURCE_TYPE = 'user-references'
    uri: str

    def _serialize_attributes(self):
        return {'user_uri': self.uri}

    def _serialize_relationships(self):
        accounts_relationship = self._format_relationship_entry(relationship_path='authorized_storage_accounts')
        return {'authorized_storage_accounts': accounts_relationship}

@dataclasses.dataclass
class _MockResourceReference(_MockGVEntity):

    RESOURCE_TYPE = 'resource-references'
    uri: str

    def _serialize_attributes(self):
        return {'resource_uri': self.uri}

    def _serialize_relationships(self):
        configured_addons_relationship = self._format_relationship_entry(relationship_path='configured_storage_addons')
        return {'configured_storage_addons': configured_addons_relationship}

@dataclasses.dataclass
class _MockAddonProvider(_MockGVEntity):

    RESOURCE_TYPE = 'external-storage-services'
    name: str
    max_upload_mb: int = 2**10
    max_concurrent_uploads: int = -5
    icon_url: str = 'vetted-url-for-icon.png'

    def _serialize_attributes(self):
        return {
            'name': self.name,
            'max_upload_mb': self.max_upload_mb,
            'max_concurrent_uploads': self.max_concurrent_uploads,
            'configurable_api_root': False,
            'terms_of_service_features': [],
            'icon_url': self.icon_url,
        }

    def _serialize_relationships(self):
        return {
            'addon_imp': self._format_relationship_entry(
                relationship_path='addon_imp', related_type='addon-imps', related_pk=1
            )
        }


@dataclasses.dataclass
class _MockAccount(_MockGVEntity):

    RESOURCE_TYPE = 'authorized-storage-accounts'
    provider: _MockAddonProvider
    account_owner_pk: int
    display_name: str = ''

    def _serialize_attributes(self):
        return {
            'display_name': self.display_name,
            'authorized_scopes': ['all_of_the_scopes'],
            'authorized_capabilities': ['ACCESS', 'UPDATE'],
            'authorized_operation_names': ['get_root_items'],
            'credentials_available': True,
        }

    def _serialize_relationships(self):
        return {
            'account_owner': self._format_relationship_entry(
                relationship_path='account_owner',
                related_type=_MockUserReference.RESOURCE_TYPE,
                related_pk=self.account_owner_pk
            ),
            'external_storage_service': self._format_relationship_entry(
                relationship_path='external_storage_service',
                related_type=_MockAddonProvider.RESOURCE_TYPE,
                related_pk=self.provider.pk
            ),
            'configured_storage_addons': self._format_relationship_entry(
                relationship_path='configured_storage_addons'
            ),
            'authorized_operations': self._format_relationship_entry(
                relationship_path='authorized_operations'
            ),
        }

@dataclasses.dataclass
class _MockAddon(_MockGVEntity):

    RESOURCE_TYPE = 'configured-storage-addons'
    resource_pk: int
    account: _MockAccount
    display_name: str = ''
    root_folder: str = '/'

    def _serialize_attributes(self):
        return {
            'display_name': self.display_name,
            'root_folder': self.root_folder,
            'max_upload_mb': self.account.provider.max_upload_mb,
            'max_concurrent_uploads': self.account.provider.max_concurrent_uploads,
            'icon_url': self.account.provider.icon_url,
            'connected_capabilities': ['ACCESS'],
            'connected_operation_names': ['get_root_items'],
        }

    def _serialize_relationships(self):
        return {
            'authorized_resource': self._format_relationship_entry(
                relationship_path='authorized_resource',
                related_type=_MockResourceReference.RESOURCE_TYPE,
                related_pk=self.resource_pk
            ),
            'base_account': self._format_relationship_entry(
                relationship_path='base_account',
                related_type=_MockAccount.RESOURCE_TYPE,
                related_pk=self.account.pk
            ),
            'external_storage_service': self._format_relationship_entry(
                relationship_path='external_storage_service',
                related_type=_MockAddonProvider.RESOURCE_TYPE,
                related_pk=self.account.provider.pk
            ),
            'connected_operations': self._format_relationship_entry(
                relationship_path='connected_operations'
            ),
        }


class MockGravyValet():

    ROUTES = {
        r'v1/user-references/((?P<pk>\d+)/|(\?filter\[user_uri\]=(?P<user_uri>.+)))$': '_get_user',
        r'v1/resource-references/((?P<pk>\d+)/|(\?filter\[resource_uri\]=(?P<resource_uri>.+)))$': '_get_resource',
        r'v1/authorized-storage-accounts/(?P<pk>\d+)/$': '_get_account',
        r'v1/configured-storage-addons/(?P<pk>\d+)/$': '_get_addon',
        r'v1/user-references/(?P<user_pk>\d+)/authorized_storage_accounts/(\?include=(?P<includes>(\w+,)+))?$': '_get_user_accounts',
        r'v1/resource-references/(?P<resource_pk>\d+)/configured_storage_addons/(\?include=(?P<includes>(\w+,)+))?$': '_get_resource_addons',
    }

    def __init__(self):
        self._clear_mappings()
        self._validate_headers = True

    @property
    def validate_headers(self) -> bool:
        return self._validate_headers

    @validate_headers.setter
    def validate_headers(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError('validate_headers must be a boolean value')
        self._validate_headers = value

    def _clear_mappings(self, include_providers: bool = True):
        """Reset all configured users/resources/acounts/addons and, optionally, providers."""
        if include_providers:
            # Mapping from _MockAddonProvider name to _MockAddonProvider
            self._known_providers = {}
        # Bidirectional mapping between user uri and mock "pk"
        self._known_users = {}
        # Bidirectional mapping between resource uri and mock "pk"
        self._known_resources = {}
        # Mapping from user "pk" to _MockAccounts for the user
        self._user_accounts = {}
        # Mapping from resource "pk" to _MockAddons "configured" on the resource
        self._resource_addons = {}

    def _get_or_create_user_entry(self, user: OSFUser):
        user_uri = user.get_semantic_iri()
        user_pk = self._known_users.get(user_uri)
        if not user_pk:
            user_pk = len(self._known_users) + 1
            self._known_users[user_uri] = user_pk
            self._known_users[user_pk] = user_uri
        return user_uri, user_pk

    def _get_or_create_resource_entry(self, resource: AbstractNode):
        resource_uri = resource.get_semantic_iri()
        resource_pk = self._known_resources.get(resource_uri)
        if not resource_pk:
            resource_pk = len(self._known_resources) + 1
            self._known_resources[resource_uri] = resource_pk
            self._known_resources[resource_pk] = resource_uri
        return resource_uri, resource_pk

    def configure_mock_provider(self, provider_name: str, **service_attrs) -> _MockAddonProvider:
        known_provider = self._known_providers.get(provider_name)
        provider_pk = known_provider.pk if known_provider else len(self._known_providers) + 1
        new_provider = _MockAddonProvider(
            name=provider_name,
            pk=provider_pk,
            **service_attrs
        )
        self._known_providers[provider_name] = new_provider
        return new_provider

    def configure_mock_account(self, user: OSFUser, addon_name: str, **account_attrs) -> _MockAccount:
        user_uri, user_pk = self._get_or_create_user_entry(user)
        account_pk = _get_nested_count(self._user_accounts) + 1
        connected_provider = self._known_providers[addon_name]
        new_account = _MockAccount(
            pk=account_pk,
            account_owner_pk=user_pk,
            provider=connected_provider,
            **account_attrs
        )
        self._user_accounts.setdefault(user_pk, []).append(new_account)
        return new_account

    def configure_mock_addon(self, resource: AbstractNode, connected_account: _MockAccount, **config_attrs) -> _MockAddon:
        resource_uri, resource_pk = self._get_or_create_resource_entry(resource)
        addon_pk = _get_nested_count(self._resource_addons) + 1
        new_addon = _MockAddon(
            pk=addon_pk,
            resource_pk=resource_pk,
            account=connected_account,
            **config_attrs
        )
        self._resource_addons.setdefault(resource_pk, []).append(new_addon)
        return new_addon

    @contextlib.contextmanager
    def run_mock(self):
        with responses.RequestsMock() as requests_mock:
            requests_mock.add_callback(
                responses.GET,
                re.compile(f'{settings.GRAVYVALET_URL}.*'),
                callback=self._route_request,
                content_type='application/json',
            )
            yield requests_mock

    def _route_request(self, request):  # -> tuple[int, dict, str]
        if self.validate_headers:
            error_response = _validate_request(request)
            if error_response:
                return error_response

        for route_expr, routed_func_name in self.ROUTES.items():
            url_regex = re.compile(f'{settings.GRAVYVALET_URL}/{route_expr}')
            route_match = url_regex.match(urllib.parse.unquote(request.url))
            if route_match:
                func = getattr(self, routed_func_name)
                return func(headers=request.headers, **route_match.groupdict())
        raise ValueError(f'No matching routes for {request.url}')

    def _get_user(
        self,
        headers: dict,
        pk=None,  # str | None
        user_uri=None,  # str | None
    ):  # -> tuple[int, dict, str]
        if not (pk or user_uri):
            raise ValueError('Must have either user PK or uri for lookup')

        # if passed the user_uri, call came through list endpoint with filter
        if user_uri:
            list_view = True
            pk = self._known_users[user_uri]
        else:
            list_view = False
            pk = int(pk)
            user_uri = self._known_users[pk]

        if self.validate_headers:
            permissions_error_response = _validate_user(user_uri, headers)
            if permissions_error_response:
                return permissions_error_response

        return _format_response(
            data=_MockUserReference(pk=pk, uri=user_uri),
            list_view=list_view
        )

    def _get_resource(
        self,
        headers: dict,
        pk=None,  # str | None
        resource_uri=None,  # str | None
    ):  # -> typing.Tuple[int, dict, str]:
        if bool(pk) == bool(resource_uri):
            raise ValueError('Must have exactly one of user PK or uri for lookup')

        if resource_uri:
            list_view = True  # call came through list endpoint with filter
            pk = self._known_resources[resource_uri]
        else:
            list_view = False
            pk = int(pk)
            resource_uri = self._known_resources[pk]

        if self.validate_headers:
            permissions_error_response = _validate_resource_access(resource_uri, headers)
            if permissions_error_response:
                return permissions_error_response

        return _format_response(
            data=_MockResourceReference(pk=pk, uri=resource_uri),
            list_view=list_view
        )

    def _get_account(self, headers: dict, pk: str):  # -> tuple[int, dict, str]
        pk = int(pk)
        account = None
        for account in itertools.chain.from_iterable(self._user_accounts.values()):
            if account.pk == pk:
                account = account
                break

        if not account:
            return (404, {}, '')  # NOT FOUND

        if self.validate_headers:
            user_uri = self._known_users[account.account_owner_pk]
            permissions_error_response = _validate_user(user_uri, headers)
            if permissions_error_response:
                return permissions_error_response

        return _format_response(data=account, list_view=False)

    def _get_addon(self, headers: dict, pk: str):  # -> tuple[int, dict, str]
        pk = int(pk)
        addon = None
        for addon in itertools.chain.from_iterable(self._resource_addons.values()):
            if addon.pk == pk:
                addon = addon
                break

        if not addon:
            return (404, {}, '')  # NOT FOUND

        if self.validate_headers:
            resource_uri = self._known_resources[addon.resource_pk]
            permissions_error_response = _validate_resource_access(resource_uri, headers)
            if permissions_error_response:
                return permissions_error_response

        return _format_response(data=addon, list_view=False)

    def _get_user_accounts(self, headers: dict, user_pk: str, includes: str = None):  # -> tuple[int, dict, str]
        user_pk = int(user_pk)
        if self.validate_headers:
            user_uri = self._known_users[user_pk]
            permissions_error_response = _validate_user(user_uri, headers)
            if permissions_error_response:
                return permissions_error_response

        return _format_response(
            data=self._user_accounts.get(user_pk, []),
            list_view=True
        )

    def _get_resource_addons(self, headers: dict, resource_pk: str, includes: str = None):  # -> tuple[int, dict, str]
        resource_pk = int(resource_pk)
        if self.validate_headers:
            resource_uri = self._known_resources[resource_pk]
            permissions_error_response = _validate_resource_access(resource_uri, headers)
            if permissions_error_response:
                return permissions_error_response

        return _format_response(
            data=self._resource_addons.get(int(resource_pk), []),
            list_view=True
        )


def _format_response(
    data,  # _MockGVEntity | list[_MockGVEntity]
    status_code: int = 200,
    list_view: bool = False,
    headers: dict = None,
):  # -> tuple[int, dict, str]:
    """Returns the expected (status, headers, json) tuple expected by callbacks for MockRequest."""
    headers = headers or {}
    serialized_data = None
    if list_view:
        if not isinstance(data, list):
            data = [data]
        serialized_data = [entry.serialize() for entry in data]
    else:
        serialized_data = data.serialize()

    response_dict = {
        'data': serialized_data
    }
    return (status_code, headers, json.dumps(response_dict))


def _get_nested_count(d):  # dict[Any, Any] -> int:
    """Get the total number of entries from a dictionary with lists for values."""
    return sum(map(len, itertools.chain(d.values())))


def _validate_request(request):
    try:
        auth_helpers.validate_signed_headers(request)
    except ValueError:
        error_code = 403 if request.headers.get('X-Requesting-User-URI') else 401
        return (error_code, {}, '')


def _validate_user(requested_user_uri, headers):
    requesting_user_uri = headers.get('X-Requesting-User-URI')
    if requesting_user_uri is None:
        return (401, {}, '')  # UNAUTHORIZED
    if requesting_user_uri != requested_user_uri:
        return (403, {}, '')  # FORBIDDEN


def _validate_resource_access(requested_resource_uri, headers):
    headers_requested_resource = headers.get('X-Requested-Resource-URI')
    if not headers_requested_resource or headers_requested_resource != requested_resource_uri:
        return (400, {}, '')  # generously assume malformed request on mismatch between headers and request
    requesting_user_uri = headers.get('X-Requesting-User-URI')
    permission_denied_error_code = 403 if requesting_user_uri else 401
    resource_permissions = headers.get('X-Requested-Resource-Permissions', '').split(';')
    if osf_permissions.READ not in resource_permissions:
        return (permission_denied_error_code, {}, '')
