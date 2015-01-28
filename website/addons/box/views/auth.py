# -*- coding: utf-8 -*-
"""OAuth views for the Box addon."""
import httplib as http
import logging
from collections import namedtuple

from flask import request
from werkzeug.wrappers import BaseResponse
#from box.client import BoxOAuth2Flow

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

from website.addons.box import settings
from website.addons.box.client import get_client_from_user_settings
#from box.rest import ErrorResponse


logger = logging.getLogger(__name__)
debug = logger.debug


def get_auth_flow():
    # Box only accepts https redirect uris unless using localhost
    redirect_uri = api_url_for('box_oauth_finish', _absolute=True)
    return BoxOAuth2Flow(
        consumer_key=settings.BOX_KEY,
        consumer_secret=settings.BOX_SECRET,
        redirect_uri=redirect_uri,
        session=session.data,
        csrf_token_session_key=settings.BOX_AUTH_CSRF_TOKEN
    )

AuthResult = namedtuple('AuthResult', ['access_token', 'box_id', 'url_state'])

def finish_auth():
    """View helper for finishing the Box Oauth2 flow. Returns the
    access_token, box_id, and url_state.

    Handles various errors that may be raised by the Box client.
    """
    try:
        access_token, box_id, url_state = get_auth_flow().finish(request.args)
    except BoxOAuth2Flow.BadRequestException:
        raise HTTPError(http.BAD_REQUEST)
    except BoxOAuth2Flow.BadStateException:
        # Start auth flow again
        return redirect(api_url_for('box_oauth_start'))
    except BoxOAuth2Flow.CsrfException:
        raise HTTPError(http.FORBIDDEN)
    except BoxOAuth2Flow.NotApprovedException:  # User canceled flow
        flash('Did not approve token.', 'info')
        return redirect(web_url_for('user_addons'))
    except BoxOAuth2Flow.ProviderException:
        raise HTTPError(http.FORBIDDEN)
    return AuthResult(access_token, box_id, url_state)


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
    # Force the user to reapprove the box authorization each time. Currently the
    # URI component force_reapprove is not configurable from the box python client.
    # Issue: https://github.com/box/box-js/issues/160
    return redirect(get_auth_flow().start() + '&force_reapprove=true')


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
    user_settings.access_token = result.access_token
    user_settings.box_id = result.box_id
    client = get_client_from_user_settings(user_settings)
    user_settings.box_info = client.account_info()
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
        client = get_client_from_user_settings(user_addon)
        client.disable_access_token()
    except ErrorResponse as error:
        if error.status == 401:
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
            client.account_info()
        except ErrorResponse as error:
            if error.status == 401:
                valid_credentials = False
            else:
                HTTPError(http.BAD_REQUEST)

    return {
        'result': {
            'userHasAuth': user_addon.has_auth,
            'validCredentials': valid_credentials,
            'boxName': info['display_name'] if info else None,
            'nNodesAuthorized': len(user_addon.nodes_authorized),
            'urls': urls
        },
    }, http.OK
