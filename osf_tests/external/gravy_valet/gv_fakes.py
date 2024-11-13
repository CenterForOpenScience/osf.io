import contextlib
import itertools
import json
import logging
import re
import typing
import urllib.parse
from functools import cache
from http import HTTPStatus

import dataclasses  # backport
import responses

from osf.external.gravy_valet import auth_helpers
from osf.models import OSFUser, AbstractNode
from osf.utils import permissions as osf_permissions
from website import settings

logger = logging.getLogger(__name__)

INCLUDE_REGEX = r'(\?include=(?P<include_param>.+))'


class FakeGVError(Exception):

    def __init__(self, status_code, *args, **kwargs):
        self.status_code = status_code
        super().__init__(*args, **kwargs)


@dataclasses.dataclass(frozen=True)
class _FakeGVEntity:
    RESOURCE_TYPE: typing.ClassVar[str]
    pk: int

    @property
    def api_path(self):
        return f'v1/{self.RESOURCE_TYPE}/{self.pk}'

    def serialize(self):
        data = {
            'type': self.RESOURCE_TYPE,
            'id': self.pk,
            'attributes': self._serialize_attributes(),
            'links': self._serialize_links(),
            'includes': self._serialize_includes(),
        }
        relationships = self._serialize_relationships()
        if relationships:
            data['relationships'] = relationships
        return data

    def _serialize_attributes(self):
        ...

    def _serialize_includes(self):
        return []

    def _serialize_relationships(self):
        ...

    def _serialize_links(self):
        return {'self': f'{settings.GRAVYVALET_URL}/{self.api_path}'}

    def _format_relationship_entry(self, relationship_path, related_type=None, related_pk=None):
        relationship_api_path = f'{settings.GRAVYVALET_URL}/{self.api_path}/{relationship_path}'
        relationship_entry = {'links': {'related': relationship_api_path}}
        if related_type and related_pk:
            relationship_entry['data'] = {'type': related_type, 'id': related_pk}
        return relationship_entry


@dataclasses.dataclass(frozen=True)
class _FakeUserReference(_FakeGVEntity):
    RESOURCE_TYPE = 'user-references'
    uri: str

    def _serialize_attributes(self):
        return {'user_uri': self.uri}

    def _serialize_relationships(self):
        accounts_storage_relationship = self._format_relationship_entry(relationship_path='authorized_storage_accounts')
        accounts_citation_relationship = self._format_relationship_entry(
            relationship_path='authorized_citation_accounts')
        return {
            'authorized_storage_accounts': accounts_storage_relationship,
            'authorized_citation_accounts': accounts_citation_relationship
        }


@dataclasses.dataclass(frozen=True)
class _FakeWBCredentials(_FakeGVEntity):
    RESOURCE_TYPE = 'waterbutler-credentials'
    config: dict

    def _serialize_attributes(self):
        return {'config': self.config}

    def _serialize_relationships(self):
        return {}


@dataclasses.dataclass(frozen=True)
class _FakeResourceReference(_FakeGVEntity):
    RESOURCE_TYPE = 'resource-references'
    uri: str

    def _serialize_attributes(self):
        return {'resource_uri': self.uri}

    def _serialize_relationships(self):
        configured_storage_addons_relationship = self._format_relationship_entry(
            relationship_path='configured_storage_addons')
        configured_citation_addons_relationship = self._format_relationship_entry(
            relationship_path='configured_citation_addons')
        return {
            'configured_storage_addons': configured_storage_addons_relationship,
            'configured_citation_addons': configured_citation_addons_relationship
        }


@dataclasses.dataclass(frozen=True)
class _FakeAddonProvider(_FakeGVEntity):
    RESOURCE_TYPE = 'external-storage-services'
    name: str
    max_upload_mb: int = 2 ** 10
    max_concurrent_uploads: int = -5
    icon_url: str = 'vetted-url-for-icon.png'
    wb_key: str = None

    def _serialize_attributes(self):
        return {
            'display_name': self.name,
            'max_upload_mb': self.max_upload_mb,
            'max_concurrent_uploads': self.max_concurrent_uploads,
            'configurable_api_root': False,
            'terms_of_service_features': [],
            'icon_url': self.icon_url,
            'wb_key': self.wb_key or self.name
        }

    def _serialize_relationships(self):
        return {
            'addon_imp': self._format_relationship_entry(
                relationship_path='addon_imp', related_type='addon-imps', related_pk=1
            )
        }


class _FakeCitationAddonProvider(_FakeAddonProvider):
    RESOURCE_TYPE = 'external-citation-services'


@dataclasses.dataclass(frozen=True)
class _FakeAccount(_FakeGVEntity):
    RESOURCE_TYPE = 'authorized-accounts'
    external_storage_service: _FakeAddonProvider | None
    external_citation_service: _FakeCitationAddonProvider | None
    account_owner_pk: int
    display_name: str = ''

    @property
    @cache
    def account_owner(self):
        return _FakeUserReference(pk=self.account_owner_pk, uri='https://osf.io/12454')

    def _serialize_attributes(self):
        return {
            'display_name': self.display_name,
            'authorized_scopes': ['all_of_the_scopes'],
            'authorized_capabilities': ['ACCESS', 'UPDATE'],
            'authorized_operation_names': ['get_root_items'],
            'credentials_available': True,
            'imp_name': 'BLARG',
        }

    def _serialize_relationships(self):
        _serialized_relationships = {
            'account_owner': self._format_relationship_entry(
                relationship_path='account_owner',
                related_type=_FakeUserReference.RESOURCE_TYPE,
                related_pk=self.account_owner_pk
            ),
            'authorized_operations': self._format_relationship_entry(
                relationship_path='authorized_operations'
            ),
        }
        if self.external_citation_service is not None:
            _serialized_relationships.update({
                'external_citation_service': self._format_relationship_entry(
                    relationship_path='external_citation_service',
                    related_type=_FakeCitationAddonProvider.RESOURCE_TYPE,
                    related_pk=self.external_storage_service.pk
                ),
                'configured_citation_addons': self._format_relationship_entry(
                    relationship_path='configured_citation_addons'
                )
            })
        if self.external_storage_service is not None:
            _serialized_relationships.update({
                'external_storage_service': self._format_relationship_entry(
                    relationship_path='external_storage_service',
                    related_type=_FakeAddonProvider.RESOURCE_TYPE,
                    related_pk=self.external_storage_service.pk
                ),
                'configured_storage_addons': self._format_relationship_entry(
                    relationship_path='configured_storage_addons'
                ),
            })
        return _serialized_relationships


@dataclasses.dataclass(frozen=True)
class _FakeAddon(_FakeGVEntity):
    RESOURCE_TYPE = 'configured-addons'
    resource_pk: int
    base_account: _FakeAccount
    display_name: str = ''
    root_folder: str = '0:1'

    def _serialize_attributes(self):
        return {
            'display_name': self.display_name,
            'root_folder': self.root_folder,
            'max_upload_mb': self.base_account.external_storage_service.max_upload_mb,
            'max_concurrent_uploads': self.base_account.external_storage_service.max_concurrent_uploads,
            'icon_url': self.base_account.external_storage_service.icon_url,
            'connected_capabilities': ['ACCESS'],
            'connected_operation_names': ['get_root_items'],
            'imp_name': 'BLARG',
        }

    def _serialize_relationships(self):
        return {
            'authorized_resource': self._format_relationship_entry(
                relationship_path='authorized_resource',
                related_type=_FakeResourceReference.RESOURCE_TYPE,
                related_pk=self.resource_pk
            ),
            'base_account': self._format_relationship_entry(
                relationship_path='base_account',
                related_type=_FakeAccount.RESOURCE_TYPE,
                related_pk=self.base_account.pk
            ),
            'external_storage_service': self._format_relationship_entry(
                relationship_path='external_storage_service',
                related_type=_FakeAddonProvider.RESOURCE_TYPE,
                related_pk=self.base_account.external_storage_service.pk
            ),
            'external_citation_service': self._format_relationship_entry(
                relationship_path='external_citation_service',
                related_type=_FakeCitationAddonProvider.RESOURCE_TYPE,
                related_pk=self.base_account.external_storage_service.pk
            ),
            'connected_operations': self._format_relationship_entry(
                relationship_path='connected_operations'
            ),
        }


class FakeGravyValet:
    ROUTES = {
        r'v1/user-references(/(?P<pk>\d+)|(\?filter\[user_uri\]=(?P<user_uri>[^&]+)))': '_get_user',
        r'v1/resource-references(/(?P<pk>\d+)|(\?filter\[resource_uri\]=(?P<resource_uri>[^&]+)))': '_get_resource',
        r'v1/authorized-storage-accounts/(?P<pk>\d+)': '_get_account',
        r'v1/authorized-citation-accounts/(?P<pk>\d+)': '_get_citation_account',
        r'v1/configured-storage-addons/(?P<pk>\d+)': '_get_addon',
        r'v1/configured-citation-addons/(?P<pk>\d+)': '_get_citation_addon',
        r'v1/configured-storage-addons/(?P<pk>\d+)/waterbutler-credentials': '_get_wb_settings',
        r'v1/user-references/(?P<user_pk>\d+)/authorized_storage_accounts': '_get_user_accounts',
        r'v1/user-references/(?P<user_pk>\d+)/authorized_citation_accounts': '_get_user_citation_accounts',
        r'v1/resource-references/(?P<resource_pk>\d+)/configured_storage_addons': '_get_resource_addons',
        r'v1/resource-references/(?P<resource_pk>\d+)/configured_citation_addons': '_get_resource_citation_addons',
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
            # Mapping from _FakeAddonProvider name to _FakeAddonProvider
            self._known_providers = {}
        # Bidirectional mapping between user uri and fake "pk"
        self._known_users = {}
        # Bidirectional mapping between resource uri and fake "pk"
        self._known_resources = {}
        # Mapping from user "pk" to _FakeAccounts for the user
        self._user_accounts = {}
        # Mapping from resource "pk" to _FakeAddons "configured" on the resource
        self._resource_addons = {}

    def _get_or_create_user_entry(self, user: OSFUser):
        user_uri = user.get_semantic_iri()
        user_pk = self._known_users.get(user_uri)
        if not user_pk:
            user_pk = len(self._known_users) + 1
            self._known_users[user_uri] = user_pk
            self._known_users[user_pk] = user_uri
        return user_uri, user_pk

    def configure_resource(self, resource: AbstractNode):
        return self._get_or_create_resource_entry(resource)

    def _get_or_create_resource_entry(self, resource: AbstractNode):
        resource_uri = resource.get_semantic_iri()
        resource_pk = self._known_resources.get(resource_uri)
        if not resource_pk:
            resource_pk = len(self._known_resources) + 1
            self._known_resources[resource_uri] = resource_pk
            self._known_resources[resource_pk] = resource_uri
        return resource_uri, resource_pk

    def configure_fake_provider(self, provider_name: str, is_citation_provider: bool = False,
                                **service_attrs) -> _FakeAddonProvider:
        known_provider = self._known_providers.get(provider_name)
        provider_pk = known_provider.pk if known_provider else len(self._known_providers) + 1
        if is_citation_provider:
            new_provider = _FakeCitationAddonProvider(
                name=provider_name,
                pk=provider_pk,
                **service_attrs
            )
        else:
            new_provider = _FakeAddonProvider(
                name=provider_name,
                pk=provider_pk,
                **service_attrs
            )
        self._known_providers[provider_name] = new_provider
        return new_provider

    def configure_fake_account(
            self,
            user: OSFUser,
            addon_name: str,
            **account_attrs
    ) -> _FakeAccount:
        user_uri, user_pk = self._get_or_create_user_entry(user)
        account_pk = _get_nested_count(self._user_accounts) + 1
        connected_provider = self._known_providers[addon_name]
        if isinstance(connected_provider, _FakeCitationAddonProvider):
            account_attrs['external_storage_service'] = None
            account_attrs['external_citation_service'] = connected_provider
        else:
            account_attrs['external_storage_service'] = connected_provider
            account_attrs['external_citation_service'] = None
        new_account = _FakeAccount(
            pk=account_pk,
            account_owner_pk=user_pk,
            **account_attrs
        )
        self._user_accounts.setdefault(user_pk, []).append(new_account)
        return new_account

    def configure_fake_addon(
            self,
            resource: AbstractNode,
            connected_account: _FakeAccount,
            **config_attrs
    ) -> _FakeAddon:
        resource_uri, resource_pk = self._get_or_create_resource_entry(resource)
        addon_pk = _get_nested_count(self._resource_addons) + 1
        new_addon = _FakeAddon(
            pk=addon_pk,
            resource_pk=resource_pk,
            base_account=connected_account,
            **config_attrs
        )
        self._resource_addons.setdefault(resource_pk, []).append(new_addon)
        return new_addon

    @contextlib.contextmanager
    def run_fake(self):
        with responses.RequestsMock() as requests_mock:
            requests_mock.add_callback(
                responses.GET,
                re.compile(f'{re.escape(settings.GRAVYVALET_URL)}.*'),
                callback=self._route_request,
                content_type='application/json',
            )
            yield requests_mock

    def _route_request(self, request):  # -> tuple[int, dict, str]
        if self.validate_headers:
            try:
                _validate_request(request)
            except FakeGVError as e:
                return (e.status_code, {}, '')

        status_code = 200
        for route_expr, routed_func_name in self.ROUTES.items():
            url_regex = re.compile(f'{re.escape(settings.GRAVYVALET_URL)}/{route_expr}({INCLUDE_REGEX}|$)')
            route_match = url_regex.match(urllib.parse.unquote(request.url))
            if route_match:
                func = getattr(self, routed_func_name)
                try:
                    body = func(headers=request.headers, **route_match.groupdict())
                except KeyError:  # entity lookup failed somewhere
                    logger.critical('BAD LOOKUP')
                    status_code = HTTPStatus.NOT_FOUND
                    body = ''
                except FakeGVError as e:
                    status_code = e.status_code
                    body = ''
                return (status_code, {}, body)

        logger.critical('route not found')
        return (HTTPStatus.NOT_FOUND, {}, '')

    def _get_user(
            self,
            headers: dict,
            pk=None,  # str | None
            user_uri=None,  # str | None
            include_param: str = '',
    ) -> str:
        if bool(pk) == bool(user_uri):
            raise FakeGVError(HTTPStatus.BAD_REQUEST)

        # if passed the user_uri, call came through list endpoint with filter
        if user_uri:
            list_view = True
            pk = self._known_users[user_uri]
        else:
            list_view = False
            pk = int(pk)
            user_uri = self._known_users[pk]

        if self.validate_headers:
            _validate_user(user_uri, headers)

        return _format_response_body(
            data=_FakeUserReference(pk=pk, uri=user_uri),
            list_view=list_view,
            include_param=include_param,
        )

    def _get_wb_settings(
            self,
            headers: dict,
            pk: str,
            include_param: str = '',
    ) -> str:
        creds = _FakeWBCredentials(
            pk=10,
            config={
                'folder': pk,
                'service': 'box',
            }
        )
        return _format_response_body(creds)

    def _get_resource(
            self,
            headers: dict,
            pk=None,  # str | None
            resource_uri=None,  # str | None
            include_param: str = '',
    ) -> str:
        if bool(pk) == bool(resource_uri):
            raise FakeGVError(HTTPStatus.BAD_REQUEST)

        # if passed the resource_uri, call came through list endpoint with filter
        if resource_uri:
            list_view = True
            pk = self._known_resources[resource_uri]
        else:
            list_view = False
            pk = int(pk)
            resource_uri = self._known_resources[pk]

        if self.validate_headers:
            _validate_resource_access(resource_uri, headers)

        return _format_response_body(
            data=_FakeResourceReference(pk=pk, uri=resource_uri),
            list_view=list_view,
            include_param=include_param,
        )

    def _get_account(
            self,
            headers: dict,
            pk: str,
            include_param: str = '',
    ) -> str:
        pk = int(pk)
        account = None
        for account in itertools.chain.from_iterable(self._user_accounts.values()):
            if account.pk == pk:
                account = account
                break

        if not account:
            logger.critical('Account not found')
            raise FakeGVError(HTTPStatus.NOT_FOUND)

        if self.validate_headers:
            user_uri = self._known_users[account.account_owner_pk]
            _validate_user(user_uri, headers)
        if account.external_storage_service is not None:
            return _format_response_body(
                data=account,
                list_view=False,
                include_param=include_param,
            )

    def _get_citation_account(
            self,
            headers: dict,
            pk: str,
            include_param: str = '',
    ) -> str:
        pk = int(pk)
        account = None
        for account in itertools.chain.from_iterable(self._user_accounts.values()):
            if account.pk == pk:
                account = account
                break

        if not account:
            logger.critical('Account not found')
            raise FakeGVError(HTTPStatus.NOT_FOUND)

        if self.validate_headers:
            user_uri = self._known_users[account.account_owner_pk]
            _validate_user(user_uri, headers)
        if account.external_citation_service is not None:
            return _format_response_body(
                data=account,
                list_view=False,
                include_param=include_param,
            )
        return _format_response_body(data=[], list_view=True)

    def _get_addon(
            self, headers: dict,
            pk: str,
            include_param: str = '',
    ) -> str:
        pk = int(pk)
        addon = None
        for addon in itertools.chain.from_iterable(self._resource_addons.values()):
            if addon.pk == pk:
                addon = addon
                break

        if not addon:
            raise FakeGVError(HTTPStatus.NOT_FOUND)

        if self.validate_headers:
            resource_uri = self._known_resources[addon.resource_pk]
            _validate_resource_access(resource_uri, headers)

        return _format_response_body(
            data=addon,
            list_view=False,
            include_param=include_param,
        )

    def _get_citation_addon(
            self, headers: dict,
            pk: str,
            include_param: str = '',
    ) -> str:
        pk = int(pk)
        addon = None
        for addon in itertools.chain.from_iterable(self._resource_addons.values()):
            if addon.pk == pk:
                addon = addon
                break

        if not addon:
            raise FakeGVError(HTTPStatus.NOT_FOUND)

        if self.validate_headers:
            resource_uri = self._known_resources[addon.resource_pk]
            _validate_resource_access(resource_uri, headers)
        if addon.base_account.external_citation_service is not None:
            return _format_response_body(
                data=addon,
                list_view=False,
                include_param=include_param,
            )
        return _format_response_body(data=[], list_view=True)

    def _get_user_accounts(
            self,
            headers: dict,
            user_pk: str,
            include_param: str = '',
    ) -> str:
        user_pk = int(user_pk)
        if self.validate_headers:
            user_uri = self._known_users[user_pk]
            _validate_user(user_uri, headers)

        return _format_response_body(
            data=self._user_accounts.get(user_pk, []),
            list_view=True,
            include_param=include_param
        )

    def _get_user_citation_accounts(
            self,
            headers: dict,
            user_pk: str,
            include_param: str = '',
    ) -> str:
        user_pk = int(user_pk)
        if self.validate_headers:
            user_uri = self._known_users[user_pk]
            _validate_user(user_uri, headers)
        if all(map(lambda x: x.external_citation_service is not None,
                   self._user_accounts.get(user_pk, []))):
            return _format_response_body(
                data=self._user_accounts.get(user_pk, []),
                list_view=True,
                include_param=include_param
            )
        return _format_response_body(data=[], list_view=True)

    def _get_resource_addons(
            self,
            headers: dict,
            resource_pk: str,
            include_param: str = '',
    ) -> str:
        resource_pk = int(resource_pk)
        if self.validate_headers:
            resource_uri = self._known_resources[resource_pk]
            _validate_resource_access(resource_uri, headers)

        return _format_response_body(
            data=self._resource_addons.get(resource_pk, []),
            include_param=include_param,
            list_view=True,
        )

    def _get_resource_citation_addons(
            self,
            headers: dict,
            resource_pk: str,
            include_param: str = '',
    ) -> str:
        resource_pk = int(resource_pk)
        if self.validate_headers:
            resource_uri = self._known_resources[resource_pk]
            _validate_resource_access(resource_uri, headers)
        if all(map(lambda x: x.base_account.external_citation_service is not None,
                   self._resource_addons.get(resource_pk, []))):
            return _format_response_body(
                data=self._resource_addons.get(resource_pk, []),
                include_param=include_param,
                list_view=True,
            )
        return _format_response_body(data=[], list_view=True)


def _format_response_body(
        data,  # _FakeGVEntity | list[_FakeGVEntity]
        list_view: bool = False,
        include_param='',
) -> str:
    """Formates the stringified json body for responses."""
    if not data:
        return json.dumps({'data': [] if list_view else None})
    if list_view:
        if not isinstance(data, list):
            data = [data]
        serialized_data = [entry.serialize() for entry in data]
    else:
        serialized_data = data.serialize()

    response_dict = {
        'data': serialized_data,
    }
    if include_param:
        response_dict['included'] = _format_includes(data, include_param.split(','))
    return json.dumps(response_dict)


def _format_includes(data, includes):
    included_data = set()
    if not isinstance(data, typing.Iterable):
        data = (data,)
    for entry in data:
        for included_path in includes:
            included_members = included_path.split('.')
            source_object = entry
            for member in included_members:
                included_entry = getattr(source_object, member)
                included_data.add(included_entry)
                source_object = included_entry
    return [included_entity.serialize() for included_entity in included_data if included_entity]


def _get_nested_count(d):  # dict[Any, Any] -> int:
    """Get the total number of entries from a dictionary with lists for values."""
    return sum(map(len, d.values()))


def _validate_request(request):
    try:
        auth_helpers.validate_signed_headers(request)
    except ValueError:
        error_code = (
            HTTPStatus.FORBIDDEN
            if request.headers.get(auth_helpers.USER_HEADER)
            else HTTPStatus.UNAUTHORIZED
        )
        raise FakeGVError(error_code)


def _validate_user(requested_user_uri, headers):
    requesting_user_uri = headers.get(auth_helpers.USER_HEADER)
    if requesting_user_uri is None:
        raise FakeGVError(HTTPStatus.UNAUTHORIZED)
    if requesting_user_uri != requested_user_uri:
        raise FakeGVError(HTTPStatus.FORBIDDEN)


def _validate_resource_access(requested_resource_uri, headers):
    headers_requested_resource = headers.get(auth_helpers.RESOURCE_HEADER)
    # generously assume malformed request on mismatch between headers and request
    if not headers_requested_resource or headers_requested_resource != requested_resource_uri:
        raise FakeGVError(HTTPStatus.BAD_REQUEST)
    requesting_user_uri = headers.get(auth_helpers.USER_HEADER)
    permission_denied_error_code = (
        HTTPStatus.FORBIDDEN if requesting_user_uri else HTTPStatus.UNAUTHORIZED
    )
    resource_permissions = headers.get(auth_helpers.PERMISSIONS_HEADER, '').split(';')
    if osf_permissions.READ not in resource_permissions:
        raise FakeGVError(permission_denied_error_code)
