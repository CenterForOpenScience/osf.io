from urllib.parse import urlencode, urljoin, urlparse, urlunparse

import logging
import dataclasses
import requests
import typing

from . import auth_helpers
from website import settings

logger = logging.getLogger(__name__)

# Use urljoin here to handle inconsistent use of trailing slash
API_BASE = urljoin(settings.GRAVYVALET_URL, 'v1/')

# {{placeholder}} format allows f-string to return a formatable string
ACCOUNT_ENDPOINT = f'{API_BASE}authorized-storage-accounts/{{pk}}'
ADDONS_ENDPOINT = f'{API_BASE}configured-storage-addons'
ADDON_ENDPOINT = f'{ADDONS_ENDPOINT}/{{pk}}'
WB_CONFIG_ENDPOINT = f'{ADDON_ENDPOINT}/waterbutler-credentials'

USER_LIST_ENDPOINT = f'{API_BASE}user-references'
USER_DETAIL_ENDPOINT = f'{API_BASE}user-references/{{pk}}'

RESOURCE_LIST_ENDPOINT = f'{API_BASE}resource-references'
RESOURCE_DETAIL_ENDPOINT = f'{API_BASE}resource-references/{{pk}}'

ACCOUNT_EXTERNAL_SERVICE_PATH = 'external_storage_service'
ACCOUNT_OWNER_PATH = 'base_account.account_owner'
ADDON_EXTERNAL_SERVICE_PATH = 'base_account.external_storage_service'


def get_account(gv_account_pk, requesting_user):  # -> JSONAPIResultEntry
    '''Return a JSONAPIResultEntry representing a known AuthorizedStorageAccount.'''
    return get_gv_result(
        endpoint_url=ACCOUNT_ENDPOINT.format(pk=gv_account_pk),
        requesting_user=requesting_user,
        params={'include': ACCOUNT_EXTERNAL_SERVICE_PATH},
    )


def create_addon(requested_resource, requesting_user, attributes: dict, relationships: dict, addon_type: str):  # -> JSONAPIResultEntry
    '''Return a JSONAPIResultEntry representing a known ConfiguredStorageAddon.'''
    json_data = {
        'attributes': attributes,
        'relationships': relationships,
        'type': addon_type,
    }
    return _make_gv_request(
        ADDONS_ENDPOINT,
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        request_method='POST',
        json_data={'data': json_data},
    )

def delete_addon(pk, requesting_user, requested_resource):
    return _make_gv_request(
        ADDON_ENDPOINT.format(pk=pk),
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        request_method='DELETE'
    )

def get_addon(gv_addon_pk, requested_resource, requesting_user):  # -> JSONAPIResultEntry
    '''Return a JSONAPIResultEntry representing a known ConfiguredStorageAddon.'''
    return get_gv_result(
        endpoint_url=ADDON_ENDPOINT.format(pk=gv_addon_pk),
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        params={'include': ADDON_EXTERNAL_SERVICE_PATH},
    )


def iterate_accounts_for_user(requesting_user):  # -> typing.Iterator[JSONAPIResultEntry]
    '''Returns an iterator of JSONAPIResultEntries representing all of the AuthorizedStorageAccounts for a user.'''
    user_result = get_gv_result(
        endpoint_url=USER_LIST_ENDPOINT,
        requesting_user=requesting_user,
        params={'filter[user_uri]': requesting_user.get_semantic_iri()},
    )
    if not user_result:
        return None
    yield from iterate_gv_results(
        endpoint_url=user_result.get_related_link('authorized_storage_accounts'),
        requesting_user=requesting_user,
        params={'include': ACCOUNT_EXTERNAL_SERVICE_PATH},
    )


def iterate_addons_for_resource(requested_resource, requesting_user):  # -> typing.Iterator[JSONAPIResultEntry]
    '''Returns an iterator of JSONAPIResultEntires representing all of the ConfiguredStorageAddons for a resource.'''
    resource_result = get_gv_result(
        endpoint_url=RESOURCE_LIST_ENDPOINT,
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        params={'filter[resource_uri]': requested_resource.get_semantic_iri()},
    )
    if not resource_result:
        return None
    yield from iterate_gv_results(
        endpoint_url=resource_result.get_related_link('configured_storage_addons'),
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        params={'include': f'{ADDON_EXTERNAL_SERVICE_PATH},{ACCOUNT_OWNER_PATH}'}
    )


def get_waterbutler_config(gv_addon_pk, requested_resource, requesting_user):  # -> JSONAPIResultEntry
    return get_gv_result(
        endpoint_url=WB_CONFIG_ENDPOINT.format(pk=gv_addon_pk),
        requesting_user=requesting_user,
        requested_resource=requested_resource
    )


def get_gv_result(
    endpoint_url: str,
    requesting_user,
    requested_resource=None,
    request_method='GET',
    params: dict = None,
):  # -> JSONAPIResultEntry
    '''Processes the result of a request to a GravyValet detail endpoint into a single JSONAPIResultEntry.'''
    response_json = _make_gv_request(
        endpoint_url=endpoint_url,
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        request_method=request_method,
        params=params,
    ).json()

    if not response_json.get('data'):
        return None
    data = response_json['data']
    if isinstance(data, list):
        data = data[0]  # Assume filtered list endpoint
    included_entities_lookup = _format_included_entities(response_json.get('included', []))
    return JSONAPIResultEntry(data, included_entities_lookup)


def get_gv_result_json(
        endpoint_url: str,
        requesting_user,
        requested_resource=None,
        request_method='GET',
        params: dict = None,
):
    '''Processes the result of a request to a GravyValet detail endpoint into a single JSONAPIResultEntry.'''
    response_json = _make_gv_request(
        endpoint_url=endpoint_url,
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        request_method=request_method,
        params=params,
    ).json()
    if not response_json['data']:
        return dict()
    return response_json['data']


def iterate_gv_results(
    endpoint_url: str,
    requesting_user,
    requested_resource=None,
    request_method='GET',
    params: dict = None,
):  # -> typing.Iterator[JSONAPIResultEntry]
    '''Processes the result of a request to GravyValet list endpoint into a generator of JSONAPIResultEntires.'''
    response_json = _make_gv_request(
        endpoint_url=endpoint_url,
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        request_method=request_method,
        params=params
    ).json()

    if not response_json['data']:
        return  # empty iterator
    included_entities_lookup = _format_included_entities(response_json.get('included', []))
    for entry in response_json['data']:
        yield JSONAPIResultEntry(entry, included_entities_lookup)


def _make_gv_request(
    endpoint_url: str,
    requesting_user,
    requested_resource=None,
    request_method='GET',
    params: dict = None,
    json_data: dict = None,
):
    '''Generates HMAC-Signed auth headers and makes a request to GravyValet, returning the result.'''
    full_url = urlunparse(urlparse(endpoint_url)._replace(query=urlencode(params or {})))
    auth_headers = auth_helpers.make_gravy_valet_hmac_headers(
        request_url=full_url,
        request_method=request_method,
        additional_headers=auth_helpers.make_permissions_headers(
            requesting_user=requesting_user,
            requested_resource=requested_resource,
        ) | {'content-type': 'application/vnd.api+json'}
    )
    assert not (request_method == 'GET' and json_data is not None)
    response = requests.request(url=endpoint_url, headers=auth_headers, params=params, method=request_method, json=json_data)
    if not response.ok:
        # log error to Sentry
        pass
    return response


def _format_included_entities(included_entities_json):
    '''Processes all entries of a JSONAPI `include` element into JSONAPIResultEntries.

    Returns a dictionary of JSONAPIResultEntires keyed by type and id for easy lookup
    and linking. Also links these entires in the case of nested Includes.
    '''
    included_entities_by_type_and_id = {
        (entity['type'], entity['id']): JSONAPIResultEntry(entity)
        for entity in included_entities_json
    }
    for entity in included_entities_by_type_and_id.values():
        entity.extract_included_relationships(included_entities_by_type_and_id)
    return included_entities_by_type_and_id

class JSONAPIResultEntry:
    resource_type: str
    resource_id: str
    _attributes: dict
    # JSONAPIRelationships keyed by relationship name
    _relationships: dict  # [str, JSONAPIRelationship]
    # Included JSONAPIResultEntries, keyed by relationship name
    _includes: dict  # [str, JSONAPIResultEntry]
    _result_entry: dict

    def __init__(self, result_entry: dict, included_entities_lookup: dict = None):
        self._result_entry = result_entry
        self.resource_type = result_entry['type']
        self.resource_id = result_entry['id']
        self._attributes = dict(result_entry['attributes'])
        if 'relationships' in result_entry:
            self._relationships = _extract_relationships(result_entry['relationships'])
        self._includes = {}
        if included_entities_lookup:
            self.extract_included_relationships(included_entities_lookup)

    def json(self):
        return self._result_entry

    def get_attribute(self, attribute_name):
        return self._attributes.get(attribute_name)

    def get_related_id(self, relationship_name):
        return self._relationships(relationship_name).related_id

    def get_related_link(self, relationship_name):
        return self._relationships[relationship_name].related_link

    def get_included_member(self, relationship_name):
        return self._includes.get(relationship_name)

    def get_included_attribute(self, include_path: typing.Iterable[str], attribute_name: str):
        related_object = self
        for relationship_name in include_path:
            related_object = related_object.get_included_member(relationship_name)
        if related_object:
            return related_object.get_attribute(attribute_name)

    def extract_included_relationships(self, included_entities_lookup):
        for relationship_entry in self._relationships.values():
            if relationship_entry.related_id is None:
                continue
            included_entity = included_entities_lookup.get(
                (relationship_entry.related_type, relationship_entry.related_id)
            )
            if included_entity:
                self._includes[relationship_entry.relationship_name] = included_entity


@dataclasses.dataclass
class JSONAPIRelationship:
    relationship_name: str
    related_link: str
    related_type: str = None
    related_id: str = None


def _extract_relationships(jsonapi_relationships_data):
    '''Converts  the `relationship entrie from a JSONAPI into a dict of JSONAPIRelationships keyed by name.'''
    relationships_by_name = {}
    for relationship_name, relationship_entry in jsonapi_relationships_data.items():
        related_data = relationship_entry.get('data', {})
        related_type = related_data.get('type')
        related_id = related_data.get('id')
        related_link = relationship_entry['links']['related']
        relationships_by_name[relationship_name] = JSONAPIRelationship(
            relationship_name=relationship_name,
            related_link=related_link,
            related_type=related_type,
            related_id=related_id
        )

    return relationships_by_name
