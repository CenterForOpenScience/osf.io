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
from oauth2client.client import AccessTokenCredentials
import requests
import json

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
    # If user has already authorized google drive, flash error message
    if user.has_addon('gdrive') and user.get_addon('gdrive').has_auth:
        flash('You have already authorized Google Drive for this account', 'warning')
        return redirect(web_url_for('user_addons'))

    flow = OAuth2WebServerFlow(settings.CLIENT_ID, settings.CLIENT_SECRET,
                               settings.OAUTH_SCOPE, redirect_uri=settings.REDIRECT_URI)
    #force the special google drive authentication screen. Google Drive only gives refresh token if this doesnt exist.
    flow.params['approval_prompt'] = 'force'
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
    #Get the refresh_token. Google sends this refresh token ONLY ONCE, right after the user first authenticates OSF
    #via the special authentication screen that Google takes user through.

    if not user_settings.refresh_token:
        user_settings.refresh_token = credentials.refresh_token
    user_settings.save()
    if node_settings:
        node_settings.user_settings = user_settings
        # # previously connected to GDrive?
        node_settings.save()
        return redirect(os.path.join(node.url, 'settings'))
    else:
        service = build('drive', 'v2', http_service)
        about = service.about().get().execute()
        username = '{0}/{1}'.format(about['name'], about['user']['emailAddress'])
        user_settings.username = username
        user_settings.save()


    #testing to see if refresh token is working.
    refresh_access_token(auth)
    return redirect(web_url_for('user_addons'))


def refresh_access_token(auth):

    #refresh_token = user_settings.refresh_token
    #make request to get new access_token
        #access_token is saved.
    #store new token as user_settings.access_token.
    if not auth.logged_in:
        raise HTTPError(http.FORBIDDEN)
    user = auth.user
    if not user.has_addon('gdrive'):
        pass# error
    user_settings = user.get_addon('gdrive')
    refresh_token = user_settings.refresh_token
    node = Node.load(session.data.get('gdrive_auth_nid'))
    payload= {
        'client_id':settings.CLIENT_ID,
        'client_secret':settings.CLIENT_SECRET,
        'refresh_token':refresh_token,
        'grant_type':'refresh_token'
    }
    payload = json.dumps(payload)
    import pdb; pdb.set_trace()
    resp = requests.post(settings.REFRESH_TOKEN_URL,data=payload)
    user_settings.access_token=resp['access_token']
    user_settings.save()
    """
    POST /oauth2/v3/token HTTP/1.1
Host: www.googleapis.com
Content-Type: application/x-www-form-urlencoded

client_id=8819981768.apps.googleusercontent.com&
client_secret={client_secret}&
refresh_token=1/6BMfW9j53gdGImsiyUH5kU5RsR4zwI9lUVX-tqf8JXQ&
grant_type=refresh_token
    """


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