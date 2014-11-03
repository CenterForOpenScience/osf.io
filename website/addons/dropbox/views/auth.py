# -*- coding: utf-8 -*-
"""OAuth views for the Dropbox addon."""
import httplib as http
import logging
from collections import namedtuple

from flask import request
from werkzeug.wrappers import BaseResponse
from dropbox.client import DropboxOAuth2Flow

from framework.auth import get_current_user
from framework.flask import redirect  # VOL-aware redirect
from framework.exceptions import HTTPError
from framework.sessions import session
from framework.status import push_status_message as flash
from framework.auth.decorators import must_be_logged_in

from website.project.model import Node
from website.project.decorators import must_have_addon
from website.util import api_url_for, web_url_for

from website.addons.dropbox import settings
from website.addons.dropbox.client import get_client_from_user_settings


logger = logging.getLogger(__name__)
debug = logger.debug


def get_auth_flow():
    # Dropbox only accepts https redirect uris unless using localhost
    redirect_uri = api_url_for('dropbox_oauth_finish', _absolute=True)
    return DropboxOAuth2Flow(
        consumer_key=settings.DROPBOX_KEY,
        consumer_secret=settings.DROPBOX_SECRET,
        redirect_uri=redirect_uri,
        session=session.data,
        csrf_token_session_key=settings.DROPBOX_AUTH_CSRF_TOKEN
    )

AuthResult = namedtuple('AuthResult', ['access_token', 'dropbox_id', 'url_state'])

def finish_auth():
    """View helper for finishing the Dropbox Oauth2 flow. Returns the
    access_token, dropbox_id, and url_state.

    Handles various errors that may be raised by the Dropbox client.
    """
    try:
        access_token, dropbox_id, url_state = get_auth_flow().finish(request.args)
    except DropboxOAuth2Flow.BadRequestException:
        raise HTTPError(http.BAD_REQUEST)
    except DropboxOAuth2Flow.BadStateException:
        # Start auth flow again
        return redirect(api_url_for('dropbox_oauth_start'))
    except DropboxOAuth2Flow.CsrfException:
        raise HTTPError(http.FORBIDDEN)
    except DropboxOAuth2Flow.NotApprovedException:  # User canceled flow
        flash('Did not approve token.', 'info')
        return redirect(web_url_for('user_addons'))
    except DropboxOAuth2Flow.ProviderException:
        raise HTTPError(http.FORBIDDEN)
    return AuthResult(access_token, dropbox_id, url_state)


@must_be_logged_in
def dropbox_oauth_start(**kwargs):
    user = get_current_user()
    # Store the node ID on the session in order to get the correct redirect URL
    # upon finishing the flow
    nid = kwargs.get('nid') or kwargs.get('pid')
    if nid:
        session.data['dropbox_auth_nid'] = nid
    if not user:
        raise HTTPError(http.FORBIDDEN)
    # If user has already authorized dropbox, flash error message
    if user.has_addon('dropbox') and user.get_addon('dropbox').has_auth:
        flash('You have already authorized Dropbox for this account', 'warning')
        return redirect(web_url_for('user_addons'))
    # Force the user to reapprove the dropbox authorization each time. Currently the
    # URI component force_reapprove is not configurable from the dropbox python client.
    # Issue: https://github.com/dropbox/dropbox-js/issues/160
    return redirect(get_auth_flow().start() + '&force_reapprove=true')


def dropbox_oauth_finish(**kwargs):
    """View called when the Oauth flow is completed. Adds a new DropboxUserSettings
    record to the user and saves the user's access token and account info.
    """
    user = get_current_user()
    if not user:
        raise HTTPError(http.FORBIDDEN)
    node = Node.load(session.data.get('dropbox_auth_nid'))
    result = finish_auth()
    # If result is a redirect response, follow the redirect
    if isinstance(result, BaseResponse):
        return result
    # Make sure user has dropbox enabled
    user.add_addon('dropbox')
    user.save()
    user_settings = user.get_addon('dropbox')
    user_settings.owner = user
    user_settings.access_token = result.access_token
    user_settings.dropbox_id = result.dropbox_id
    client = get_client_from_user_settings(user_settings)
    user_settings.dropbox_info = client.account_info()
    user_settings.save()

    flash('Successfully authorized Dropbox', 'success')
    if node:
        del session.data['dropbox_auth_nid']
        # Automatically use newly-created auth
        if node.has_addon('dropbox'):
            node_addon = node.get_addon('dropbox')
            node_addon.set_user_auth(user_settings)
            node_addon.save()
        return redirect(node.web_url_for('node_setting'))
    return redirect(web_url_for('user_addons'))

@must_be_logged_in
@must_have_addon('dropbox', 'user')
def dropbox_oauth_delete_user(user_addon, auth, **kwargs):
    """View for deauthorizing Dropbox."""
    client = get_client_from_user_settings(user_addon)
    user_addon.clear()
    user_addon.save()
    client.disable_access_token()
    return None


@must_be_logged_in
@must_have_addon('dropbox', 'user')
def dropbox_user_config_get(user_addon, auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Dropbox user settings.
    """
    urls = {
        'create': api_url_for('dropbox_oauth_start_user'),
        'delete': api_url_for('dropbox_oauth_delete_user')
    }
    info = user_addon.dropbox_info
    return {
        'result': {
            'userHasAuth': user_addon.has_auth,
            'dropboxName': info['display_name'] if info else None,
            'urls': urls,
        },
    }, http.OK
