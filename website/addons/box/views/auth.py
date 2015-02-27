# -*- coding: utf-8 -*-
"""OAuth views for the Box addon."""
import time
import logging
import httplib as http
from datetime import datetime

import furl
import requests
from flask import request
from box import BoxClient, CredentialsV2
from werkzeug.wrappers import BaseResponse

from framework.flask import redirect  # VOL-aware redirect
from framework.sessions import session
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from framework.status import push_status_message as flash

from website.util import api_url_for
from website.util import web_url_for
from website import security
from website.project.model import Node
from website.project.decorators import must_have_addon

from box.client import BoxClientException
from website.addons.box import settings
from website.addons.box.model import BoxOAuthSettings
from website.addons.box.utils import handle_box_error
from website.addons.box.client import get_client_from_user_settings

logger = logging.getLogger(__name__)


def get_auth_flow(csrf_token):
    url = furl.furl(settings.BOX_OAUTH_AUTH_ENDPOINT)

    url.args = {
        'state': csrf_token,
        'response_type': 'code',
        'client_id': settings.BOX_KEY,
        'redirect_uri': api_url_for('box_oauth_finish', _absolute=True),
    }

    return url.url


def finish_auth():
    """View helper for finishing the Box Oauth2 flow. Returns the
    access_token, user_id, and url_state.

    Handles various errors that may be raised by the Box client.
    """
    if 'error' in request.args:
        handle_box_error(error=request.args['error'], msg=request.args['error_description'])

    # Should always be defined
    code = request.args['code']
    # Default to empty string over None because of below assertion
    state = request.args.get('state', '')

    if state != session.data.pop('box_oauth_state', None):
        raise HTTPError(http.FORBIDDEN)

    data = {
        'code': code,
        'client_id': settings.BOX_KEY,
        'grant_type': 'authorization_code',
        'client_secret': settings.BOX_SECRET,
    }

    response = requests.post(settings.BOX_OAUTH_TOKEN_ENDPOINT, data)
    result = response.json()

    if 'error' in result:
        handle_box_error(error=request.args['error'], msg=request.args['error_description'])

    return result


@must_be_logged_in
def box_oauth_start(auth, **kwargs):
    user = auth.user
    # Store the node ID on the session in order to get the correct redirect URL
    # upon finishing the flow
    nid = kwargs.get('nid') or kwargs.get('pid')

    node = Node.load(nid)

    if node and not node.is_contributor(user):
        raise HTTPError(http.FORBIDDEN)

    csrf_token = security.random_string(10)
    session.data['box_oauth_state'] = csrf_token

    if nid:
        session.data['box_auth_nid'] = nid

    # If user has already authorized box, flash error message
    if user.has_addon('box') and user.get_addon('box').has_auth:
        flash('You have already authorized Box for this account', 'warning')
        return redirect(web_url_for('user_addons'))

    return redirect(get_auth_flow(csrf_token))


@must_be_logged_in
def box_oauth_finish(auth, **kwargs):
    """View called when the Oauth flow is completed. Adds a new BoxUserSettings
    record to the user and saves the user's access token and account info.
    """
    user = auth.user
    node = Node.load(session.data.pop('box_auth_nid', None))

    # Handle request cancellations from Box's API
    if request.args.get('error'):
        flash('Box authorization request cancelled.')
        if node:
            return redirect(node.web_url_for('node_setting'))
        return redirect(web_url_for('user_addons'))

    result = finish_auth()

    # If result is a redirect response, follow the redirect
    if isinstance(result, BaseResponse):
        return result

    client = BoxClient(CredentialsV2(
        result['access_token'],
        result['refresh_token'],
        settings.BOX_KEY,
        settings.BOX_SECRET,
    ))

    about = client.get_user_info()
    oauth_settings = BoxOAuthSettings.load(about['id'])

    if not oauth_settings:
        oauth_settings = BoxOAuthSettings(user_id=about['id'], username=about['name'])
        oauth_settings.save()

    oauth_settings.refresh_token = result['refresh_token']
    oauth_settings.access_token = result['access_token']
    oauth_settings.expires_at = datetime.utcfromtimestamp(time.time() + 3600)

    # Make sure user has box enabled
    user.add_addon('box')
    user.save()

    user_settings = user.get_addon('box')
    user_settings.oauth_settings = oauth_settings

    user_settings.save()

    flash('Successfully authorized Box', 'success')

    if node:
        # Automatically use newly-created auth
        if node.has_addon('box'):
            node_addon = node.get_addon('box')
            node_addon.set_user_auth(user_settings)
            node_addon.save()
        return redirect(node.web_url_for('node_setting'))
    return redirect(web_url_for('user_addons'))


@must_be_logged_in
@must_have_addon('box', 'user')
def box_oauth_delete_user(user_addon, auth, **kwargs):
    """View for deauthorizing Box."""
    user_addon.clear()
    user_addon.save()


@must_be_logged_in
@must_have_addon('box', 'user')
def box_user_config_get(user_addon, auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Box user settings.
    """
    urls = {
        'create': api_url_for('box_oauth_start_user'),
        'delete': api_url_for('box_oauth_delete_user')
    }
    valid_credentials = True

    if user_addon.has_auth:
        try:
            client = get_client_from_user_settings(user_addon)
            client.get_user_info()
        except BoxClientException:
            valid_credentials = False

    return {
        'result': {
            'urls': urls,
            'boxName': user_addon.username,
            'userHasAuth': user_addon.has_auth,
            'validCredentials': valid_credentials,
            'nNodesAuthorized': len(user_addon.nodes_authorized),
        },
    }
