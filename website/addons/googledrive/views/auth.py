import httplib2
import httplib as http
from datetime import datetime

from flask import request

from framework.flask import redirect  # VOL-aware redirect
from framework.sessions import session
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from framework.status import push_status_message as flash

from website import models
from website.util import permissions
from website.util import web_url_for
from website.project.model import Node
from website.project.decorators import must_have_addon
from website.project.decorators import must_have_permission

from website.addons.googledrive.client import GoogleAuthClient
from website.addons.googledrive.client import GoogleDriveClient
from website.addons.googledrive.utils import serialize_settings


@must_be_logged_in
def googledrive_oauth_start(auth, **kwargs):
    """View function that does OAuth Authorization
    and returns access token"""
    # Run through the OAuth flow and retrieve credentials
    # Store the node ID on the session in order to get the correct redirect URL
    # upon finishing the flow
    user = auth.user
    nid = kwargs.get('nid') or kwargs.get('pid')
    node = models.Node.load(nid) if nid else None
    node_addon = user.get_addon('googledrive')

    # Fail if node provided and user not contributor
    if node and not node.is_contributor(user):
        raise HTTPError(http.FORBIDDEN)

    # If user has already authorized google drive, flash error message
    if node_addon and node_addon.has_auth:
        flash('You have already authorized Google Drive for this account', 'warning')
        return redirect(web_url_for('user_addons'))

    client = GoogleAuthClient()
    authorization_url, state = client.start()

    session.data['googledrive_auth_state'] = state
    if nid:
        session.data['googledrive_auth_nid'] = nid

    return {'url': authorization_url}


@must_be_logged_in
def googledrive_oauth_finish(auth, **kwargs):
    """View called when the Oauth flow is completed. Adds a new GoogleDriveUserSettings
    record to the user and saves the user's access token and account info.
    """
    user = auth.user
    user.add_addon('googledrive')
    user.save()

    code = request.args.get('code')
    user_settings = user.get_addon('googledrive')
    node = Node.load(session.data.get('googledrive_auth_nid'))
    state = session.data.get('googledrive_auth_state')
    del session.data['googledrive_auth_state']

    if state != request.args.get('state'):
        raise HTTPError(http.BAD_REQUEST)

    if code is None:
        raise HTTPError(http.BAD_REQUEST)

    auth_client = GoogleAuthClient()
    token = auth_client.finish(code)

    user_settings.access_token = token['access_token']
    user_settings.refresh_token = token['refresh_token']
    user_settings.token_expires_at = datetime.utcfromtimestamp(token['expires_at'])

    drive_client = GoogleDriveClient(token['access_token'])
    about = drive_client.about()

    user_settings.username = about['name']
    user_settings.save()

    flash('Successfully authorized Google Drive', 'success')
    if node:
        del session.data['googledrive_auth_nid']
        if node.has_addon('googledrive'):
            node_addon = node.get_addon('googledrive')
            node_addon.set_user_auth(user_settings)
            node_addon.save()
        return redirect(node.web_url_for('node_setting'))
    return redirect(web_url_for('user_addons'))


@must_be_logged_in
@must_have_addon('googledrive', 'user')
def googledrive_oauth_delete_user(user_addon, **kwargs):
    client = GoogleAuthClient()
    client.revoke(user_addon.access_token)
    user_addon.clear()
    user_addon.save()


@must_have_permission(permissions.WRITE)
@must_have_addon('googledrive', 'node')
def googledrive_deauthorize(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth)
    node_addon.save()


@must_have_permission(permissions.WRITE)
@must_have_addon('googledrive', 'node')
def googledrive_import_user_auth(auth, node_addon, **kwargs):
    """Import googledrive credentials from the currently logged-in user to a node.
    """
    user = auth.user
    user_addon = user.get_addon('googledrive')

    if user_addon is None:
        raise HTTPError(http.BAD_REQUEST)

    node_addon.set_user_auth(user_addon)
    node_addon.save()
    return {
        'result': serialize_settings(node_addon, user),
        'message': 'Successfully imported access token from profile.',
    }
