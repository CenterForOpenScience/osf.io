import waffle
from flask import request

from api.base.utils import is_truthy
from osf import features
from osf.external.gravy_valet.request_helpers import _make_gv_request, get_gv_result_json, RESOURCE_LIST_ENDPOINT, \
    get_gv_result
from osf.models import Node
from osf.utils.permissions import WRITE
from website import settings
from website.citations.views import GenericCitationViews
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_contributor_or_public
)
from .provider import ZoteroCitationsProvider


class ZoteroViews(GenericCitationViews):
    def set_config(self):
        addon_short_name = self.addon_short_name
        Provider = self.Provider

        @must_not_be_registration
        @must_have_addon(addon_short_name, 'user')
        @must_have_addon(addon_short_name, 'node')
        @must_be_addon_authorizer(addon_short_name)
        @must_have_permission(WRITE)
        def _set_config(node_addon, user_addon, auth, **kwargs):
            """ Changes folder associated with addon.
            Returns serialized node settings
            """
            provider = Provider()
            args = request.get_json()
            external_list_id = args.get('external_list_id')
            external_list_name = args.get('external_list_name')
            external_library_id = args.get('external_library_id', None)
            external_library_name = args.get('external_library_name', None)
            provider.set_config(
                node_addon,
                auth.user,
                external_list_id,
                external_list_name,
                auth,
                external_library_id,
                external_library_name
            )
            return {
                'result': provider.serializer(
                    node_settings=node_addon,
                    user_settings=auth.user.get_addon(addon_short_name),
                ).serialized_node_settings
            }

        _set_config.__name__ = f'{addon_short_name}_set_config'
        return _set_config

    def library_list(self):
        addon_short_name = self.addon_short_name

        @must_be_contributor_or_public
        @must_have_addon(addon_short_name, 'node')
        def _library_list(auth, node_addon, **kwargs):
            """ Returns a list of group libraries - for use with Zotero addon
            """

            limit = request.args.get('limit')
            start = request.args.get('start')
            return_count = is_truthy(request.args.get('return_count', False))
            append_personal = is_truthy(request.args.get('append_personal', True))
            if not waffle.flag_is_active(request, features.ENABLE_GV):
                return node_addon.get_folders(limit=limit, start=start, return_count=return_count,
                                              append_personal=append_personal)
            else:
                response = []
                project_ulr = settings.DOMAIN + request.view_args.get('pid')
                project = Node.objects.filter(guids___id__in=[request.view_args.get('pid')]).first()
                resource_references_response = get_gv_result(
                    endpoint_url=RESOURCE_LIST_ENDPOINT,
                    requesting_user=auth.user,
                    requested_resource=project,
                    params={'filter[resource_uri]': project_ulr},
                )
                configured_storage_addons_url = resource_references_response.get_related_link(
                    'configured_storage_addons')
                addons_url_list = get_gv_result_json(
                    endpoint_url=configured_storage_addons_url,
                    requesting_user=auth.user,
                    requested_resource=project,
                    request_method='GET',
                    params={}
                )
                # citation_list = list(
                #     filter(lambda x: x['attributes']['external_service_name'] == addon_short_name, addons_url_list))

                # resource_references_response = get_gv_result(
                #     endpoint_url=USER_LIST_ENDPOINT,
                #     requesting_user=auth.user,
                #     params={'filter[user_uri]': f'{settings.DOMAIN}/{auth.user._id}'},
                # )
                for addon in addons_url_list:
                    gv_response = _make_gv_request(
                        endpoint_url=f'{settings.GRAVYVALET_URL}/v1/addon-operation-invocations/',
                        requesting_user=auth.user,
                        requested_resource=project,
                        request_method='POST',
                        params={},
                        data={
                            'data': {
                                'attributes': {
                                    'operation_name': 'list_root_items',
                                    'operation_kwargs': {},
                                },
                                'relationships': {
                                    'thru_addon': {
                                        'data': {
                                            'type': addon['type'],
                                            'id': addon['id']
                                        }
                                    }
                                },
                                'type': 'addon-operation-invocations'
                            }
                        }

                    )
                    if gv_response.status_code == 201:
                        attributes_dict = gv_response.json()['data']['attributes']
                        items = attributes_dict.get('operation_result').get('items')
                        item_id = items[0].get('item_id', '')
                        response.append({
                            'addon': addon_short_name,
                            'kind': items[0].get('item_type', '').lower(),
                            'id': item_id,
                            'name': items[0].get('item_name', ''),
                            'path': items[0].get('item_path', ''),
                            'parent_list_id': None,
                            'provider_list_id': item_id,
                        })
                return response

        _library_list.__name__ = f'{addon_short_name}_library_list'
        return _library_list


zotero_views = ZoteroViews('zotero', ZoteroCitationsProvider)
