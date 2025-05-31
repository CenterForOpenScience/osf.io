import dataclasses
import enum
import logging
import typing
from urllib.parse import urlencode, urljoin, urlparse, urlunparse

import requests
from requests.exceptions import RequestException

from website import settings
from . import auth_helpers

logger = logging.getLogger(__name__)

# Use urljoin here to handle inconsistent use of trailing slash
API_BASE = urljoin(settings.GRAVYVALET_URL, 'v1/')

# {{placeholder}} format allows f-string to return a formatable string
ACCOUNT_ENDPOINT = f'{API_BASE}authorized-storage-accounts/{{pk}}'
ADDONS_ENDPOINT = f'{API_BASE}configured-storage-addons'
GENERIC_ADDONS_ENDPOINT = f'{API_BASE}{{addon_type}}'
ADDON_ENDPOINT = f'{GENERIC_ADDONS_ENDPOINT}/{{pk}}'
WB_CONFIG_ENDPOINT = f'{ADDON_ENDPOINT}/waterbutler-credentials'

USER_LIST_ENDPOINT = f'{API_BASE}user-references'
USER_DETAIL_ENDPOINT = f'{API_BASE}user-references/{{pk}}'

RESOURCE_LIST_ENDPOINT = f'{API_BASE}resource-references'
RESOURCE_DETAIL_ENDPOINT = f'{API_BASE}resource-references/{{pk}}'
ACCOUNT_EXTERNAL_STORAGE_SERVICE_PATH = 'external_storage_service'
ACCOUNT_EXTERNAL_COMPUTING_SERVICE_PATH = 'external_computing_service'
ACCOUNT_EXTERNAL_CITATION_SERVICE_PATH = 'external_citation_service'
ACCOUNT_EXTERNAL_SERVICE_ENDPOINT = f'{API_BASE}external-{{addon_type}}-services'
ACCOUNT_OWNER_PATH = 'base_account.account_owner'
ADDON_EXTERNAL_STORAGE_SERVICE_PATH = 'base_account.external_storage_service'
ADDON_EXTERNAL_CITATIONS_SERVICE_PATH = 'base_account.external_citation_service'
ADDON_EXTERNAL_COMPUTING_SERVICE_PATH = 'base_account.external_computing_service'


class AddonType(enum.StrEnum):
    STORAGE = enum.auto()
    CITATION = enum.auto()
    COMPUTING = enum.auto()

CITATION_ITEM_TYPE_ALIASES = {
    'COLLECTION': 'folder',
    'DOCUMENT': 'file',
}


def get_account(gv_account_pk, requesting_user):  # -> JSONAPIResultEntry
    '''Return a JSONAPIResultEntry representing a known AuthorizedStorageAccount.'''
    return get_gv_result(
        endpoint_url=ACCOUNT_ENDPOINT.format(pk=gv_account_pk),
        requesting_user=requesting_user,
        params={'include': ACCOUNT_EXTERNAL_STORAGE_SERVICE_PATH},
    )


def create_addon(requested_resource, requesting_user, attributes: dict, relationships: dict, addon_type: str):  # -> JSONAPIResultEntry
    '''Return a JSONAPIResultEntry representing a known ConfiguredStorageAddon.'''
    json_data = {
        'attributes': attributes,
        'relationships': relationships,
        'type': addon_type,
    }
    return _make_gv_request(
        GENERIC_ADDONS_ENDPOINT.format(addon_type=addon_type),
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        request_method='POST',
        json_data={'data': json_data},
    )

def delete_addon(pk, requesting_user, requested_resource, addon_type: str):
    return _make_gv_request(
        ADDON_ENDPOINT.format(pk=pk, addon_type=addon_type),
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        request_method='DELETE',
    )

def get_addon(gv_addon_pk, requested_resource, requesting_user, addon_type: str):  # -> JSONAPIResultEntry
    '''Return a JSONAPIResultEntry representing a known ConfiguredStorageAddon.'''
    return get_gv_result(
        endpoint_url=ADDON_ENDPOINT.format(pk=gv_addon_pk, addon_type=addon_type),
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        params={'include': ADDON_EXTERNAL_STORAGE_SERVICE_PATH},
    )


def iterate_accounts_for_user(requesting_user, addon_type=None):  # -> typing.Iterator[JSONAPIResultEntry]
    '''Returns an iterator of JSONAPIResultEntries representing all of the AuthorizedStorageAccounts for a user.'''
    user_result = get_gv_result(
        endpoint_url=USER_LIST_ENDPOINT,
        requesting_user=requesting_user,
        params={'filter[user_uri]': requesting_user.get_semantic_iri()},
    )
    if not user_result:
        return None
    if not addon_type or addon_type == AddonType.STORAGE:
        yield from iterate_gv_results(
            endpoint_url=user_result.get_related_link('authorized_storage_accounts'),
            requesting_user=requesting_user,
            params={'include': f'{ACCOUNT_EXTERNAL_STORAGE_SERVICE_PATH}'}
        )
    if not addon_type or addon_type == AddonType.CITATION:
        yield from iterate_gv_results(
            endpoint_url=user_result.get_related_link('authorized_citation_accounts'),
            requesting_user=requesting_user,
            params={'include': f'{ACCOUNT_EXTERNAL_CITATION_SERVICE_PATH}'}
        )
    if not addon_type or addon_type == AddonType.COMPUTING:
        yield from iterate_gv_results(
            endpoint_url=user_result.get_related_link('authorized_computing_accounts'),
            requesting_user=requesting_user,
            params={'include': f'{ACCOUNT_EXTERNAL_COMPUTING_SERVICE_PATH}'}
        )


def iterate_addons_for_resource(requested_resource, requesting_user, addon_type=None, auth=None):  # -> typing.Iterator[JSONAPIResultEntry]
    '''Returns an iterator of JSONAPIResultEntires representing all of the ConfiguredStorageAddons for a resource.'''
    resource_result = get_gv_result(
        endpoint_url=RESOURCE_LIST_ENDPOINT,
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        params={'filter[resource_uri]': requested_resource.get_semantic_iri()},
        auth=auth,
    )
    if not resource_result:
        return None
    if not addon_type or addon_type == AddonType.STORAGE:
        yield from iterate_gv_results(
            endpoint_url=resource_result.get_related_link('configured_storage_addons'),
            requesting_user=requesting_user,
            requested_resource=requested_resource,
            params={'include': f'{ADDON_EXTERNAL_STORAGE_SERVICE_PATH},{ACCOUNT_OWNER_PATH}'},
            auth=auth,
        )
    if not addon_type or addon_type == AddonType.CITATION:
        yield from iterate_gv_results(
            endpoint_url=resource_result.get_related_link('configured_citation_addons'),
            requesting_user=requesting_user,
            requested_resource=requested_resource,
            params={'include': f'{ADDON_EXTERNAL_CITATIONS_SERVICE_PATH},{ACCOUNT_OWNER_PATH}'},
            auth=auth,
        )
    if not addon_type or addon_type == AddonType.COMPUTING:
        yield from iterate_gv_results(
            endpoint_url=resource_result.get_related_link('configured_computing_addons'),
            requesting_user=requesting_user,
            requested_resource=requested_resource,
            params={'include': f'{ADDON_EXTERNAL_COMPUTING_SERVICE_PATH},{ACCOUNT_OWNER_PATH}'},
            auth=auth,
        )


def get_waterbutler_config(gv_addon_pk, requested_resource, requesting_user, addon_type):  # -> JSONAPIResultEntry
    return get_gv_result(
        endpoint_url=WB_CONFIG_ENDPOINT.format(pk=gv_addon_pk, addon_type=addon_type),
        requesting_user=requesting_user,
        requested_resource=requested_resource
    )


def get_gv_result(
    endpoint_url: str,
    requesting_user,
    requested_resource=None,
    request_method='GET',
    params: dict = None,
    auth=None
):  # -> JSONAPIResultEntry
    '''Processes the result of a request to a GravyValet detail endpoint into a single JSONAPIResultEntry.'''
    response = _make_gv_request(
        endpoint_url=endpoint_url,
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        request_method=request_method,
        params=params,
        auth=auth,
    )
    if not response:
        return
    response_json = response.json()

    if not response_json.get('data'):
        return None
    data = response_json['data']
    if isinstance(data, list):
        data = data[0]  # Assume filtered list endpoint
    included_entities_lookup = _format_included_entities(response_json.get('included', []))
    return JSONAPIResultEntry(data, included_entities_lookup)


def get_raw_gv_result(
        endpoint_url: str,
        requesting_user,
        requested_resource=None,
        request_method='GET',
        params: dict = None,
        auth=None,
):
    '''Processes the result of a request to a GravyValet detail endpoint into a single JSONAPIResultEntry.'''
    response = _make_gv_request(
        endpoint_url=endpoint_url,
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        request_method=request_method,
        params=params,
        auth=auth
    )
    if not response:
        return {}
    response_json = response.json()
    if not response_json.get('data'):
        return {}
    return response_json['data']


def iterate_gv_results(
    endpoint_url: str,
    requesting_user,
    requested_resource=None,
    request_method='GET',
    params: dict = None,
    auth=None
):  # -> typing.Iterator[JSONAPIResultEntry]
    '''Processes the result of a request to GravyValet list endpoint into a generator of JSONAPIResultEntires.'''
    response = _make_gv_request(
        endpoint_url=endpoint_url,
        requesting_user=requesting_user,
        requested_resource=requested_resource,
        request_method=request_method,
        params=params,
        auth=auth
    )
    if not response:
        return

    response_json = response.json()
    if not response_json.get('data'):
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
    auth=None,
):
    '''Generates HMAC-Signed auth headers and makes a request to GravyValet, returning the result.'''
    full_url = urlunparse(urlparse(endpoint_url)._replace(query=urlencode(params or {})))
    auth_headers = auth_helpers.make_gravy_valet_hmac_headers(
        request_url=full_url,
        request_method=request_method,
        additional_headers=auth_helpers.make_permissions_headers(
            requesting_user=requesting_user,
            requested_resource=requested_resource,
            auth=auth,
        ) | {'content-type': 'application/vnd.api+json'}
    )
    assert not (request_method == 'GET' and json_data is not None)
    try:
        response = requests.request(url=endpoint_url, headers=auth_headers, params=params, method=request_method, json=json_data)
    except RequestException as e:
        logger.error(f"Cannot reach GravyValet: {e}")
        return None
    if not response.ok:
        # log error to Sentry
        logger.error(f"GV request failed with status code {response.status_code}")
        pass
    return response


def get_gv_citation_url_list_for_project(auth, project, request=None, pid=None) -> dict:
    if pid:
        project_url = settings.DOMAIN + pid
    else:
        project_url = settings.DOMAIN + request.view_args.get('pid')
    resource_references_response = get_gv_result(
        endpoint_url=RESOURCE_LIST_ENDPOINT,
        requesting_user=auth.user,
        requested_resource=project,
        params={'filter[resource_uri]': project_url},
        auth=auth
    )
    if not resource_references_response:
        return {}
    configured_citation_addons_url = resource_references_response.get_related_link('configured_citation_addons')
    addon_list = get_raw_gv_result(
        endpoint_url=configured_citation_addons_url,
        requesting_user=auth.user,
        requested_resource=project,
        request_method='GET',
        params={},
        auth=auth
    )
    return {
        addon['attributes']['external_service_name']: addon for addon in addon_list
    }

def _invoke_gv_citation_operation_invocations(auth, addon, project, list_id):
    data = {
        'attributes': {
            'operation_name': 'list_collection_items',
            'operation_kwargs': {
                'collection_id': addon['attributes']['root_folder'] if list_id == 'ROOT' else list_id
            },
        },
        'relationships': {
            'thru_addon': {
                'data': {
                    'type': 'configured-citation-addons',
                    'id': addon['id']
                }
            }
        },
        'type': 'addon-operation-invocations'
    }
    gv_response = _make_gv_request(
        endpoint_url=f'{settings.GRAVYVALET_URL}/v1/addon-operation-invocations/',
        requesting_user=auth.user,
        requested_resource=project,
        request_method='POST',
        params={},
        json_data={'data': data},
        auth=auth
    )
    return gv_response


def citation_list_gv_request(auth, request, addon_short_name, list_id, show):
    from osf.models import Node

    contents = []
    project = Node.objects.filter(guids___id__in=[request.view_args.get('pid')]).first()
    addon = get_gv_citation_url_list_for_project(
        auth=auth,
        request=request,
        project=project
    )[addon_short_name]
    gv_response = _invoke_gv_citation_operation_invocations(
        auth=auth,
        addon=addon,
        project=project,
        list_id=list_id,
    )
    if gv_response.status_code == 201:
        attributes_dict = gv_response.json()['data']['attributes']
        items = attributes_dict.get('operation_result').get('items')
        for item in items:
            item_id = item.get('item_id', '')
            kind = CITATION_ITEM_TYPE_ALIASES.get(item.get('item_type', ''))
            if 'csl' in item.keys():
                change_response = item
                change_response['kind'] = kind
                change_response['id'] = item_id
            else:
                change_response = {
                    'data': {
                        'addon': addon_short_name,
                        'kind': kind,
                        'id': item_id,
                        'name': item.get('item_name', ''),
                        'path': item.get('item_path', '/'),
                        'parent_list_id': item.get('parent_list_id', 'ROOT'),
                        'provider_list_id': item_id,
                    },
                    'kind': kind,
                    'name': item.get('item_name', ''),
                    'id': item_id,
                    'urls': {
                        'fetch': f'/api/v1/project/{project._id}/{addon_short_name}/citations/{item_id}/',
                    }
                }
            contents.append(change_response)
    return {'contents': contents}


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

    def get_included_member(self, *relationship_path: str):
        related_object = self
        for relationship_name in relationship_path:
            related_object = related_object._includes.get(relationship_name)
        return related_object

    def get_included_attribute(self, include_path: typing.Iterable[str], attribute_name: str):
        related_object = self.get_included_member(*include_path)
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
        if relationship_entry is not None:
            related_data = relationship_entry.get('data') or {}
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
