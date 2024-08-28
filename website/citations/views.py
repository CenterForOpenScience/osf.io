import waffle
from django.db.models import Q
from flask import request

from framework.auth.decorators import must_be_logged_in
from osf import features
from osf.external.gravy_valet.request_helpers import _make_gv_request, get_gv_result, \
    RESOURCE_LIST_ENDPOINT, get_gv_result_json
from osf.models import Node
from osf.models.citation import CitationStyle
from osf.utils.permissions import WRITE
from website import settings
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_valid_project, must_be_contributor_or_public
)


def list_citation_styles():
    query = request.args.get('q')
    citation_styles = CitationStyle.objects.all()
    if query:
        citation_styles = CitationStyle.objects.filter(
            Q(_id__icontains=query) |
            Q(title__icontains=query) |
            Q(short_title__icontains=query)
        )
    return {
        'styles': [style.to_json() for style in citation_styles if style.has_bibliography]
    }


@must_be_contributor_or_public
def node_citation(**kwargs):
    node = kwargs['node'] or kwargs['project']
    return {node.csl['id']: node.csl}


## Generics ##

class GenericCitationViews:
    """
    Generic class for citation view functions.
    Citation addons must instantiate a GenericCitationViews
    object with the addon short name and provider, then
    define routes as call to that objects function, due to
    how these view functions are wrapped.

    Example:
    ```
    ## in /addons/citation/views.py
    citation_views = GenericCitationViews('citations', CitationsProvider)

    ## in /addons/citation/routes.py
    Rule(
        [routes],
        'get',
        citation_views.account_list(),
        json_renderer,
    ),
    """

    addon_short_name = None
    Provider = None

    def __init__(self, addon_short_name, Provider):
        self.addon_short_name = addon_short_name
        self.Provider = Provider

    def account_list(self):
        addon_short_name = self.addon_short_name
        Provider = self.Provider

        @must_be_logged_in
        def _account_list(auth):
            """ List addon accounts associated with the currently logged-in user
            """
            return Provider().user_accounts(auth.user)

        _account_list.__name__ = f'{addon_short_name}_account_list'
        return _account_list

    def get_config(self):
        addon_short_name = self.addon_short_name
        Provider = self.Provider

        @must_be_logged_in
        @must_have_addon(addon_short_name, 'node')
        @must_be_valid_project
        @must_have_permission(WRITE)
        def _get_config(auth, node_addon, **kwargs):
            """ Returns the serialized node settings,
            with a boolean indicator for credential validity.
            """
            provider = Provider()
            result = provider.serializer(
                node_settings=node_addon,
                user_settings=auth.user.get_addon(addon_short_name)
            ).serialized_node_settings
            result['validCredentials'] = provider.check_credentials(node_addon)
            return {'result': result}

        _get_config.__name__ = f'{addon_short_name}_get_config'
        return _get_config

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
            provider.set_config(
                node_addon,
                auth.user,
                external_list_id,
                external_list_name,
                auth,
            )
            return {
                'result': provider.serializer(
                    node_settings=node_addon,
                    user_settings=auth.user.get_addon(addon_short_name),
                ).serialized_node_settings
            }

        _set_config.__name__ = f'{addon_short_name}_set_config'
        return _set_config

    def import_auth(self):
        addon_short_name = self.addon_short_name
        Provider = self.Provider

        @must_not_be_registration
        @must_have_addon(addon_short_name, 'user')
        @must_have_addon(addon_short_name, 'node')
        @must_have_permission(WRITE)
        def _import_auth(auth, node_addon, user_addon, **kwargs):
            """
            Import addon credentials from the currently logged-in user to a node.
            """
            provider = Provider()
            external_account_id = request.get_json().get('external_account_id')
            return provider.add_user_auth(node_addon, auth.user, external_account_id)

        _import_auth.__name__ = f'{addon_short_name}_import_auth'
        return _import_auth

    def deauthorize_node(self):
        addon_short_name = self.addon_short_name
        Provider = self.Provider

        @must_not_be_registration
        @must_have_addon(addon_short_name, 'node')
        @must_have_permission(WRITE)
        def _deauthorize_node(auth, node_addon, **kwargs):
            """ Removes addon authorization from node.
            """
            provider = Provider()
            return provider.remove_user_auth(node_addon, auth.user)

        _deauthorize_node.__name__ = f'{addon_short_name}_deauthorize_node'
        return _deauthorize_node

    def widget(self):
        addon_short_name = self.addon_short_name
        Provider = self.Provider

        @must_be_contributor_or_public
        @must_have_addon(addon_short_name, 'node')
        def _widget(node_addon, **kwargs):
            """ Collects and serializes settting needed to build the widget
            """
            return Provider().widget(node_addon)

        _widget.__name__ = f'{addon_short_name}_widget'
        return _widget

    def citation_list(self):
        addon_short_name = self.addon_short_name
        Provider = self.Provider

        @must_be_contributor_or_public
        @must_have_addon(addon_short_name, 'node')
        def _citation_list(auth, node_addon, list_id=None, **kwargs):
            """ Returns a list of citations
            """

            show = request.args.get('view', 'all')
            if not waffle.flag_is_active(request, features.ENABLE_GV):
                return Provider().citation_list(node_addon, auth.user, list_id, show)
            else:
                response = dict(contents=[])
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

                        change_response = {
                            'data': {
                                'addon': addon_short_name,
                                'kind': items[0].get('item_type', '').lower(),
                                'id': item_id,
                                'name': items[0].get('item_name', ''),
                                'path': items[0].get('item_path', ''),
                                'parent_list_id': 'ROOT',
                                'provider_list_id': items[0].get('item_id', ''),
                            },
                            'kind': items[0].get('item_type', '').lower(),
                            'name': items[0].get('item_name', ''),
                            'id': item_id,
                            'urls': {
                                'fetch': f'/api/v1/project/{project._id}/{addon_short_name}/citations/{item_id}/',
                            }
                        }
                        response['contents'].append(change_response)
                return response

        _citation_list.__name__ = f'{addon_short_name}_citation_list'
        return _citation_list
