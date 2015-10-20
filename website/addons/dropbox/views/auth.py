# -*- coding: utf-8 -*-
"""OAuth views for the Dropbox addon."""
import httplib as http
import logging

from dropbox.rest import ErrorResponse

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.project.decorators import must_have_addon
from website.addons.dropbox.serializer import DropboxSerializer
from website.addons.dropbox.client import get_client_from_user_settings

logger = logging.getLogger(__name__)
debug = logger.debug

@must_be_logged_in
@must_have_addon('dropbox', 'user')
def dropbox_oauth_delete_user(user_addon, auth, **kwargs):
    """View for deauthorizing Dropbox."""
    try:
        client = get_client_from_user_settings(user_addon)
        client.disable_access_token()
    except ErrorResponse as error:
        if error.status == 401:
            pass
        else:
            raise HTTPError(http.BAD_REQUEST)
    user_addon.delete()
    user_addon.save()

    return None


@must_be_logged_in
def dropbox_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Dropbox user settings.
    """
    serializer = DropboxSerializer(user_settings=auth.user.get_addon('dropbox'))
    return serializer.serialized_user_settings
