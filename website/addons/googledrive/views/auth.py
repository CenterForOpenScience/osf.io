import httplib2
import httplib as http

from flask import request
from apiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow

from framework.flask import redirect  # VOL-aware redirect
from framework.sessions import session
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from framework.status import push_status_message as flash

from website.util import api_url_for
from website.util import permissions
from website.util import web_url_for
from website.project.model import Node
from website.project.decorators import must_have_addon
from website.project.decorators import must_have_permission

from website.addons.googledrive import settings
from website.addons.googledrive.utils import serialize_settings


@must_be_logged_in
def googledrive_oauth_start(auth, **kwargs):
    """View function that does OAuth Authorization
    and returns access token"""
    # Run through the OAuth flow and retrieve credentials
    # Store the node ID on the session in order to get the correct redirect URL
    # upon finishing the flow
    nid = kwargs.get('nid') or kwargs.get('pid')
    node_addon = auth.user.get_addon('googledrive')

    if nid:
        session.data['googledrive_auth_nid'] = nid

    # If user has already authorized google drive, flash error message
    if node_addon and node_addon.has_auth:
        flash('You have already authorized Google Drive for this account', 'warning')
        return redirect(web_url_for('user_addons'))

    redirect_uri = api_url_for('googledrive_oauth_finish', _absolute=True)
    flow = OAuth2WebServerFlow(
        settings.CLIENT_ID,
        settings.CLIENT_SECRET,
        settings.OAUTH_SCOPE,
        redirect_uri=redirect_uri
    )
    flow.params['approval_prompt'] = 'force'
    authorize_url = flow.step1_get_authorize_url()
    return {'url': authorize_url}


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

    if code is None:
        raise HTTPError(http.BAD_REQUEST)

    redirect_uri = api_url_for('googledrive_oauth_finish', _absolute=True)
    flow = OAuth2WebServerFlow(
        settings.CLIENT_ID,
        settings.CLIENT_SECRET,
        settings.OAUTH_SCOPE,
        redirect_uri=redirect_uri
    )
    credentials = flow.step2_exchange(code)
    http_service = httplib2.Http()
    http_service = credentials.authorize(http_service)

    user_settings.access_token = credentials.access_token
    user_settings.refresh_token = credentials.refresh_token
    # Add No. of seconds left for token to expire into current utc time
    user_settings.token_expires_at = credentials.token_expiry

    # Retrieves username for authorized google drive
    service = build('drive', 'v2', http_service)
    about = service.about().get().execute()
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
    }, http.OK
