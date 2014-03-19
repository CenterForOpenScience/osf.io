# -*- coding: utf-8 -*-
"""OAuth views for the Dropbox addon."""
import httplib as http
import os
import logging

from dropbox.client import DropboxOAuth2Flow

from framework.auth import get_current_user
from framework.exceptions import HTTPError
from framework.sessions import session
from framework import redirect, request
from framework.status import push_status_message as flash
from framework.auth.decorators import must_be_logged_in
from website.project.model import Node
from website.project.decorators import must_have_addon
from website.util import api_url_for, web_url_for

from website.addons.dropbox import settings, model
from website.addons.dropbox.client import get_client_from_user_settings


logger = logging.getLogger(__name__)
debug = logger.debug


def get_auth_flow():
    redirect_uri = api_url_for('dropbox_oauth_finish', _external=True)
    return DropboxOAuth2Flow(
        consumer_key=settings.DROPBOX_KEY,
        consumer_secret=settings.DROPBOX_SECRET,
        redirect_uri=redirect_uri,
        session=session.data,
        csrf_token_session_key=settings.DROPBOX_AUTH_CSRF_TOKEN
    )


@must_be_logged_in
def dropbox_oauth_start(**kwargs):
    user = get_current_user()
    if not user:
        raise HTTPError(http.FORBIDDEN)
    # If user has already authorized dropbox, flash error message
    if user.has_addon('dropbox') and user.get_addon('dropbox').has_auth:
        flash('You have already authorized Github for this account', 'warning')
        return redirect(web_url_for('profile_settings'))
    return redirect(get_auth_flow().start())


def dropbox_oauth_finish(**kwargs):
    user = get_current_user()
    node = Node.load(kwargs.get('nid'))
    if not user:
        raise HTTPError(http.FORBIDDEN)

    # Handle various errors that may be raised by the dropbox client
    try:
        access_token, dropbox_id, url_state = get_auth_flow().finish(request.args)
    except DropboxOAuth2Flow.BadRequestException:
        raise HTTPError(http.BAD_REQUEST)
    except DropboxOAuth2Flow.BadStateException:
        # Start auth flow again
        redirect(api_url_for('dropbox_oauth_start'))
    except DropboxOAuth2Flow.CsrfException:
        raise HTTPError(http.FORBIDDEN)
    except DropboxOAuth2Flow.NotApprovedException:
        flash('Could not approve token.')
        return redirect(web_url_for('profile_settings'))
    except DropboxOAuth2Flow.ProviderException:
        raise HTTPError(http.FORBIDDEN)

    user_settings = user.get_addon('dropbox') or model.DropboxUserSettings()

    user_settings.owner = user
    user_settings.access_token = access_token
    user_settings.dropbox_id = dropbox_id
    user_settings.save()

    flash('Successfully authenticated with Dropbox', 'success')
    if node:
        return redirect(os.path.join(node.url, 'settings'))
    return redirect(web_url_for('profile_settings'))


@must_have_addon('dropbox', 'user')
def dropbox_oauth_delete_user(**kwargs):
    user_settings = kwargs['user_addon']
    client = get_client_from_user_settings(user_settings)
    client.disable_access_token()
    user_settings.clear_auth()
    user_settings.save()
    flash('Removed token', 'info')
    return {}
