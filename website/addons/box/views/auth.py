# -*- coding: utf-8 -*-
"""OAuth views for the Box addon."""
import httplib as http
import requests
from urllib import urlencode
import logging
from datetime import datetime

from flask import request
from werkzeug.wrappers import BaseResponse

from framework.flask import redirect  # VOL-aware redirect
from framework.sessions import session
from framework.exceptions import HTTPError
from framework.auth.decorators import collect_auth
from framework.auth.decorators import must_be_logged_in
from framework.status import push_status_message as flash

from website.util import api_url_for
from website.util import web_url_for
from website.project.model import Node
from website.project.decorators import must_have_addon

from box.client import BoxClientException
from website.addons.box import settings
from website.addons.box.client import get_client_from_user_settings, disable_access_token

logger = logging.getLogger(__name__)
debug = logger.debug


def get_auth_flow():
    args = {
        'response_type': 'code',
        'client_id': settings.BOX_KEY,
        'state': 'security_token_needed',
        'redirect_uri': api_url_for('box_oauth_finish', _absolute=True),
    }

    return 'https://www.box.com/api/oauth2/authorize?' + urlencode(args)


def finish_auth():
    """View helper for finishing the Box Oauth2 flow. Returns the
    access_token, box_id, and url_state.

    Handles various errors that may be raised by the Box client.
    """
    if 'code' in request.args:
        code = request.args['code']
        # url_state = request.args['state']
    elif 'error' in request.args:
        box_error_handle(error=request.args['error'], msg=request.args['error_description'])

    # This can be used for added security. A 'state' is passed to box, and it will return
    # the same state after authorization. It may return a different or no state if the
    # request has been hijacked
    # if url_state is not 'security_token_needed':
    #     raise HTTPError(http.INTERNAL_SERVER_ERROR)

    args = {
        'client_id': settings.BOX_KEY,
        'client_secret': settings.BOX_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
    }
    response = requests.post('https://www.box.com/api/oauth2/token', args)
    result = response.json()
    if 'error' in result:
        box_error_handle(error=request.args['error'], msg=request.args['error_description'])
    return result


@must_be_logged_in
def box_oauth_start(auth, **kwargs):
    user = auth.user
    # Store the node ID on the session in order to get the correct redirect URL
    # upon finishing the flow
    nid = kwargs.get('nid') or kwargs.get('pid')
    if nid:
        session.data['box_auth_nid'] = nid
    if not user:
        raise HTTPError(http.FORBIDDEN)
    # If user has already authorized box, flash error message
    if user.has_addon('box') and user.get_addon('box').has_auth:
        flash('You have already authorized Box for this account', 'warning')
        return redirect(web_url_for('user_addons'))
    return redirect(get_auth_flow())


@collect_auth
def box_oauth_finish(auth, **kwargs):
    """View called when the Oauth flow is completed. Adds a new BoxUserSettings
    record to the user and saves the user's access token and account info.
    """
    if not auth.logged_in:
        raise HTTPError(http.FORBIDDEN)
    user = auth.user

    node = Node.load(session.data.get('box_auth_nid'))
    result = finish_auth()
    # If result is a redirect response, follow the redirect
    if isinstance(result, BaseResponse):
        return result
    # Make sure user has box enabled
    user.add_addon('box')
    user.save()
    user_settings = user.get_addon('box')
    user_settings.owner = user
    user_settings.last_refreshed = datetime.utcnow()
    user_settings.restricted_to = result['restricted_to']
    user_settings.token_type = result['token_type']
    user_settings.access_token = result['access_token']
    user_settings.refresh_token = result['refresh_token']
    client = get_client_from_user_settings(user_settings)
    user_settings.box_info = client.get_user_info()
    user_settings.box_id = user_settings.box_info['id']
    user_settings.save()

    flash('Successfully authorized Box', 'success')
    if node:
        del session.data['box_auth_nid']
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
    try:
        disable_access_token(user_addon)
    except BoxClientException as error:
        if error.status_code == 401:
            pass
        else:
            raise HTTPError(http.BAD_REQUEST)
    user_addon.clear()
    user_addon.save()

    return None


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
    info = user_addon.box_info
    valid_credentials = True

    if user_addon.has_auth:
        try:
            client = get_client_from_user_settings(user_addon)
            client.get_user_info()
        except BoxClientException as error:
            if error.status_code == 401:
                valid_credentials = False
            else:
                HTTPError(http.BAD_REQUEST)

    return {
        'result': {
            'userHasAuth': user_addon.has_auth,
            'validCredentials': valid_credentials,
            'boxName': info if info else None,
            'nNodesAuthorized': len(user_addon.nodes_authorized),
            'urls': urls
        },
    }, http.OK


def box_error_handle(error, msg):
    if (error is 'invalid_request' or 'unsupported_response_type'):
        raise HTTPError(http.BAD_REQUEST)
    if (error is 'access_denied'):
        raise HTTPError(http.FORBIDDEN)
    if (error is 'server_error'):
        raise HTTPError(http.INTERNAL_SERVER_ERROR)
    if (error is 'temporarily_unavailable'):
        raise HTTPError(http.SERVICE_UNAVAILABLE)
    raise HTTPError(http.INTERNAL_SERVER_ERROR)
