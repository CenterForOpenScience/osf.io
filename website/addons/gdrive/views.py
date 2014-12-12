# -*- coding: utf-8 -*-
import os
from flask import request
from framework.auth.core import _get_current_user
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in, collect_auth
from framework.flask import redirect # VOL-aware redirect
from framework.status import push_status_message as flash
from framework.sessions import session
import httplib as http
import httplib2
from website.project.model import Node
from website.project.decorators import (must_be_valid_project,
    must_have_addon, must_have_permission, must_not_be_registration
)
from website.util import api_url_for
from website.util import web_url_for
from .utils import serialize_settings, serialize_urls

from apiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow
from apiclient import errors

import settings

# TODO
@must_be_valid_project
@must_have_addon('gdrive', 'node')
def gdrive_config_get(node_addon, **kwargs):
    """API that returns the serialized node settings."""
    user = _get_current_user()
    return {
        'result': serialize_settings(node_addon, user),
    }, http.OK



@must_be_logged_in
def drive_oauth_start(auth, **kwargs):
    """View function that does OAuth Authorization
    and returns access token"""
   # Run through the OAuth flow and retrieve credentials
    user = auth.user
    # Store the node ID on the session in order to get the correct redirect URL
    # upon finishing the flow
    if not user:
        raise HTTPError(http.FORBIDDEN)

    nid = kwargs.get('nid') or kwargs.get('pid')
    if nid:
        session.data['gdrive_auth_nid'] = nid
    # If user has already authorized dropbox, flash error message
    if user.has_addon('gdrive') and user.get_addon('gdrive').has_auth:
        flash('You have already authorized Google Drive for this account', 'warning')
        return redirect(web_url_for('user_addons'))
    flow = OAuth2WebServerFlow(settings.CLIENT_ID, settings.CLIENT_SECRET, settings.OAUTH_SCOPE, redirect_uri = settings.REDIRECT_URI)
    authorize_url = flow.step1_get_authorize_url()
    return{'url' : authorize_url}

@collect_auth
def drive_oauth_finish(auth, **kwargs):

    user = auth.user
    if not auth.logged_in:
        raise HTTPError(http.FORBIDDEN)

    user.add_addon('gdrive')
    user.save()
    user_settings = user.get_addon('gdrive')
    node = Node.load(session.data.get('gdrive_auth_nid'))
    node_settings = node.get_addon('gdrive') if node else None
    code = request.args.get('code')
    if code is None:
        raise HTTPError(http.BAD_REQUEST)

    flow = OAuth2WebServerFlow(settings.CLIENT_ID, settings.CLIENT_SECRET, settings.OAUTH_SCOPE, redirect_uri = settings.REDIRECT_URI)
    credentials = flow.step2_exchange(code)
    http_service = httplib2.Http()
    http_service = credentials.authorize(http_service)
    settings.SERVICE = build('drive', 'v2', http_service)
    user_settings.access_token = credentials.access_token
    user_settings.save()
    if node_settings:
        node_settings.user_settings = user_settings
        # # previously connected to GDrive?
        node_settings.save()
        return redirect(os.path.join(node.url, 'settings'))
    return redirect(web_url_for('user_addons'))


@must_be_logged_in
@must_have_addon('gdrive', 'user')
def drive_oauth_delete_user(user_addon, auth, **kwargs):
    user_addon.clear()
    user_addon.save()


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('gdrive', 'node')
def gdrive_config_put(node_addon, auth, **kwargs):
    """View for changing a node's linked gdrive folder."""
    folder = request.json.get('selected')
    path = folder['path']
    node_addon.set_folder(path, auth=auth)
    node_addon.save()
    return {
        'result': {
            'folder': {
                'name': 'Dropbox' + path,
                'path': path
            },
            'urls': serialize_urls(node_addon)
        },
        'message': 'Successfully updated settings.',
    }, http.OK


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



@must_be_logged_in
def get_children(**kwargs):

   auth = kwargs['auth']
   user = auth.user

   nid = kwargs.get('nid') or kwargs.get('pid')
   node_addon= Node.load(nid)
   node_settings = node_addon.get_addon('gdrive')
   if node_settings:
       user_settings = node_settings.user_settings
       service = settings.SERVICE
   folderid = request.args.get('folder-id')
   result = retrieve_all_files(service, folderid)
   return {
      'result' : result
   }


def retrieve_all_files(service, folderId):
  """Retrieve a list of File resources.

  Args:
    service: Drive API service instance.
  Returns:
    List of File resources.
  """
  result = []
  page_token = None
  while True:
    try:
      param = {}
      if page_token:
        param['pageToken'] = page_token
      if service:
        files = service.files().list(q= "'%s' in parents and trashed = false" % folderId).execute()
        result.extend(files['items'])
        page_token = files.get('nextPageToken')
        if not page_token:
            break
    except errors.HttpError, error:
      print 'An error occurred: %s' % error
      break
  return result



@must_be_logged_in
@must_have_addon('gdrive', 'user')
def drive_user_config_get(user_addon, auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    GDrive user settings.
    """
    urls = {
        'create': api_url_for('drive_oauth_start_user'),
        'delete': api_url_for('drive_oauth_delete_user'),
    }

    return {
        'result': {
            'userHasAuth': user_addon.has_auth,
            'urls': urls
        },
    }, http.OK