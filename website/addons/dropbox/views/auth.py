# -*- coding: utf-8 -*-
"""OAuth views for the Dropbox addon."""
import httplib as http
import os

from dropbox.client import DropboxOAuth2Flow

from website.util import api_url_for, web_url_for
from framework.auth import get_current_user
from framework.exceptions import HTTPError
from framework.sessions import session
from framework import redirect, request
from framework.status import push_status_message as flash

from website.project.model import Node
from website.addons.dropbox import settings, model


def get_auth_flow():
    redirect_uri = api_url_for('dropbox_oauth_finish', _external=True)
    return DropboxOAuth2Flow(
        consumer_key=settings.DROPBOX_KEY,
        consumer_secret=settings.DROPBOX_SECRET,
        redirect_uri=redirect_uri,
        session=session.data,
        csrf_token_session_key=settings.DROPBOX_AUTH_CSRF_TOKEN
    )


def dropbox_oauth_start(**kwargs):
    user = get_current_user()
    if not user:
        raise HTTPError(http.FORBIDDEN)
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

    user_settings = model.DropboxUserSettings(
        owner=user,
        access_token=access_token,
        dropbox_id=dropbox_id
    )
    user_settings.save()

    if node:
        return redirect(os.path.join(node.url, 'settings'))
    return redirect(web_url_for('profile_settings'))
