import os
import httplib as http
import httplib2

from ..import settings
from ..utils import serialize_settings
from flask import request
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in, collect_auth
from framework.flask import redirect  # VOL-aware redirect
from framework.status import push_status_message as flash
from framework.sessions import session
from website.project.model import Node
from website.util import web_url_for
from oauth2client.client import OAuth2WebServerFlow
from website.project.decorators import (must_have_addon, must_have_permission)
from apiclient.discovery import build
import time

@must_be_logged_in
def drive_oauth_start(auth, **kwargs):
    """View function that does OAuth Authorization
    and returns access token"""
    # Run through the OAuth flow and retrieve credentials
    user = auth.user
    if not user:
        raise HTTPError(http.FORBIDDEN)
    # Store the node ID on the session in order to get the correct redirect URL
    # upon finishing the flow
    nid = kwargs.get('nid') or kwargs.get('pid')
    if nid:
        session.data['gdrive_auth_nid'] = nid
    # If user has already authorized dropbox, flash error message
    if user.has_addon('gdrive') and user.get_addon('gdrive').has_auth:
        flash('You have already authorized Google Drive for this account', 'warning')
        return redirect(web_url_for('user_addons'))
    flow = OAuth2WebServerFlow(settings.CLIENT_ID, settings.CLIENT_SECRET,
                               settings.OAUTH_SCOPE, redirect_uri=settings.REDIRECT_URI)

    flow.params['approval_prompt']='force'
    authorize_url = flow.step1_get_authorize_url()
    return{'url': authorize_url}

@collect_auth
def drive_oauth_finish(auth, **kwargs):
    """View called when the Oauth flow is completed. Adds a new AddonGdriveUserSettings
    record to the user and saves the user's access token and account info.
    """
    if not auth.logged_in:
        raise HTTPError(http.FORBIDDEN)
    user = auth.user
    user.add_addon('gdrive')
    user.save()
    user_settings = user.get_addon('gdrive')
    node = Node.load(session.data.get('gdrive_auth_nid'))
    node_settings = node.get_addon('gdrive') if node else None
    code = request.args.get('code')
    if code is None:
        raise HTTPError(http.BAD_REQUEST)

    flow = OAuth2WebServerFlow(settings.CLIENT_ID, settings.CLIENT_SECRET,
                               settings.OAUTH_SCOPE, redirect_uri=settings.REDIRECT_URI)
    credentials = flow.step2_exchange(code)
    http_service = httplib2.Http()
    http_service = credentials.authorize(http_service)
    user_settings.access_token = credentials.access_token
    user_settings.refresh_token = credentials.refresh_token


    cur_time_in_millis = int(round(time.time() * 1000))
    user_settings.token_expiry = cur_time_in_millis + credentials.token_expiry
    user_settings.save()

    if node_settings:
        node_settings.user_settings = user_settings
        # # previously connected to GDrive?
        node_settings.save()
        return redirect(os.path.join(node.url, 'settings'))
    else:
        service = build('drive', 'v2', http_service)
        about = service.about().get().execute()
        username = about['name']
        user_settings.username = username
        user_settings.save()
    return redirect(web_url_for('user_addons'))


@must_be_logged_in
@must_have_addon('gdrive', 'user')
def drive_oauth_delete_user(user_addon, auth, **kwargs):
    user_addon.clear()
    user_addon.save()


@must_have_permission('write')
@must_have_addon('gdrive', 'node')
def gdrive_deauthorize(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth)
    node_addon.save()
    return None


@must_have_permission('write')
@must_have_addon('gdrive', 'node')
def gdrive_import_user_auth(auth, node_addon, **kwargs):
    """Import gdrive credentials from the currently logged-in user to a node.
    """
    user = auth.user
    user_addon = user.get_addon('gdrive')
    if user_addon is None or node_addon is None:
        raise HTTPError(http.BAD_REQUEST)
    node_addon.set_user_auth(user_addon)
    node_addon.save()
    return {
        'result': serialize_settings(node_addon, user),
        'message': 'Successfully imported access token from profile.',
    }, http.OK