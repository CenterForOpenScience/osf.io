import httplib as http

from framework import request
from framework.exceptions import HTTPError
from framework.auth import get_current_user

from website.util import web_url_for
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_valid_project
)

from ..api import Figshare
from ..utils import options_to_hgrid


###### AJAX Config
@must_be_valid_project
@must_have_addon('figshare', 'node')
def figshare_config_get(node_addon, **kwargs):
    """API that returns the serialized node settings."""
    user = get_current_user()
    return {
        'result': serialize_settings(node_addon, user),
    }, http.OK


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('figshare', 'node')
@must_be_addon_authorizer('figshare')
def figshare_config_put(node_addon, auth, **kwargs):
    """View for changing a node's linked figshare folder."""
    fields = request.json.get('selected', {})
    node = node_addon.owner
    node_addon.update_fields(fields, node, auth)

    return {
        'result': {
            'linked': {
                'title': fields.get('title') or '',
                'id': fields.get('id') or None,
                'type': fields.get('type') or None
            },
            'urls': serialize_urls(node_addon)
        },
        'message': 'Successfully updated settings.',
    }, http.OK


@must_have_permission('write')
@must_have_addon('figshare', 'node')
def figshare_import_user_auth(auth, node_addon, **kwargs):
    """Import figshare credentials from the currently logged-in user to a node.
    """
    user = auth.user
    user_addon = user.get_addon('figshare')
    if user_addon is None or node_addon is None:
        raise HTTPError(http.BAD_REQUEST)
    node_addon.authorize(user_addon, save=True)
    return {
        'result': serialize_settings(node_addon, user),
        'message': 'Successfully imported access token from profile.',
    }, http.OK


@must_have_permission('write')
@must_have_addon('figshare', 'node')
def figshare_deauthorize(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth, save=True)
    return {}


def serialize_settings(node_settings, current_user, client=None):
    """View helper that returns a dictionary representation of a
    FigshareNodeSettings record. Provides the return value for the
    figshare config endpoints.
    """    

    current_user_settings = current_user.get_addon('figshare')
    user_settings = node_settings.user_settings
    user_has_auth = current_user_settings is not None and current_user_settings.has_auth
    user_is_owner = user_settings is not None and (
        user_settings.owner._primary_key == current_user._primary_key
    )

    result = {
        'nodeHasAuth': node_settings.has_auth,
        'userHasAuth': user_has_auth,
        'userIsOwner': user_is_owner,
        'urls': serialize_urls(node_settings)
    }

    if node_settings.has_auth:
        # Add owner's profile URL
        result['urls']['owner'] = web_url_for('profile_view_id',
            uid=user_settings.owner._primary_key)
        result['ownerName'] = user_settings.owner.fullname
        # Show available projects
        linked = node_settings.linked_content or {'id': None, 'type': None, 'title': None}
        result['linked'] = linked
    return result


def serialize_urls(node_settings):
    node = node_settings.owner
    urls = {
        'config': node.api_url_for('figshare_config_put'),
        'deauthorize': node.api_url_for('figshare_deauthorize'),
        'auth': node.api_url_for('figshare_oauth_start'),
        'importAuth': node.api_url_for('figshare_import_user_auth'),
        'options': node.api_url_for('figshare_get_options'),
        'files': node.web_url_for('collect_file_trees__page'),
        # Endpoint for fetching only folders (including root)
        'contents': node.api_url_for('figshare_hgrid_data_contents'),
    }
    return urls


@must_be_valid_project
@must_have_addon('figshare', 'node')
def figshare_get_options(node_addon, **kwargs):
    options = Figshare.from_settings(node_addon.user_settings).get_options()

    # TODO: Fix error handling
    if options == 401 or not isinstance(options, list):
        raise HTTPError(http.BAD_REQUEST)
        # self.user_settings.remove_auth()
        # push_status_message(messages.OAUTH_INVALID)
    else:
        node = node_addon.owner
        return options_to_hgrid(node, options) or []
