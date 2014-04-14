import httplib as http

from framework import request
from framework.exceptions import HTTPError
from framework.auth import get_current_user

from website.project.decorators import must_have_permission
from website.project.decorators import must_have_addon
from website.project.decorators import must_not_be_registration
from website.project.decorators import (must_have_addon,
    must_have_permission, must_not_be_registration,
    must_be_valid_project
)


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
def figshare_config_put(node_addon, auth, **kwargs):
    """View for changing a node's linked figshare folder."""
    folder = request.json.get('selected')
    path = folder['path']
    node_addon.set_folder(path, auth=auth)
    node_addon.save()
    return {
        'result': {
            'folder': {
                'name': 'Figshare' + path,
                'path': path
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
    node_addon.set_user_auth(user_addon)
    node_addon.save()
    return {
        'result': serialize_settings(node_addon, user),
        'message': 'Successfully imported access token from profile.',
    }, http.OK

@must_have_permission('write')
@must_have_addon('figshare', 'node')
def figshare_deauthorize(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth)
    node_addon.save()
    return None

def serialize_settings(node_settings, current_user, client=None):
    """View helper that returns a dictionary representation of a
    FigshareNodeSettings record. Provides the return value for the
    figshare config endpoints.
    """
    user_settings = current_user.get_addon('figshare')
    user_has_auth = user_settings is not None and user_settings.has_auth
    result = {
        'nodeHasAuth': node_settings.has_auth,
        'userHasAuth': user_has_auth,
        'urls': serialize_urls(node_settings)
    }
    if node_settings.has_auth:
        # Add owner's profile URL
        result['urls']['owner'] = web_url_for('profile_view_id',
            uid=user_settings.owner._primary_key)
        result['ownerName'] = user_settings.owner.fullname
        # Show available projects
        '''
        path = node_settings.folder
        if path is None:
            result['folder'] = {'name': None, 'path': None}
        else:
            result['folder'] = {
                'name': 'Figshare' + path,
                'path': path
            }
        '''
    return result


##############

@must_have_permission('write')
@must_not_be_registration
@must_have_addon('figshare', 'node')
def figshare_set_config(*args, **kwargs):

    auth = kwargs['auth']
    node_settings = kwargs['node_addon']
    node = node_settings.owner

    # If authorized, only owner can change settings
    if not node_settings.has_auth or node_settings.user_settings.owner != auth.user:
        raise HTTPError(http.BAD_REQUEST)

    try:
        figshare_title = request.json.get('figshare_title', '')
        figshare_url = request.json.get('figshare_value', '').split('_')
        figshare_type = figshare_url[0]
        figshare_id = figshare_url[1]
    except:
        raise HTTPError(http.BAD_REQUEST)

    if not figshare_id or not (figshare_type == 'project' or figshare_type == 'fileset'):
        raise HTTPError(http.BAD_REQUEST)

    changed = (
        figshare_id != node_settings.figshare_id or
        figshare_type != node_settings.figshare_type or
        figshare_title != node_settings.figshare_title
    )
    if changed:
        node_settings.figshare_id = figshare_id
        node_settings.figshare_type = figshare_type
        node_settings.figshare_title = figshare_title
        node_settings.save()

        node.add_log(
            action='figshare_content_linked',
            params={
                'project': node.parent_id,
                'node': node._id,
                'figshare': {
                    'type': figshare_type,
                    'id': figshare_id,
                    'title': figshare_title,
                }
            },
            auth=auth,
        )
    return {}


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('figshare', 'node')
def figshare_unlink(*args, **kwargs):
    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    figshare_node = node.get_addon('figshare')

    # If authorized, only owner can change settings
    if not figshare_node.user_settings or figshare_node.user_settings.owner != auth.user:
        raise HTTPError(http.BAD_REQUEST)
    node.add_log(
        action='figshare_content_unlinked',
        params={
            'project': node.parent_id,
            'node': node._id,
            'figshare': {
                'type': figshare_node.figshare_type,
                'id': figshare_node.figshare_id
            }
        },
        auth=auth,
    )
    figshare_node.figshare_id = None
    figshare_node.figshare_type = None
    figshare_node.figshare_title = None
    figshare_node.save()
