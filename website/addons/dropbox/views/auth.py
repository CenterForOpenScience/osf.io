# -*- coding: utf-8 -*-
"""OAuth views for the Dropbox addon."""
import logging

from framework.auth.decorators import must_be_logged_in

from website.addons.dropbox.serializer import DropboxSerializer

logger = logging.getLogger(__name__)
debug = logger.debug

@must_be_logged_in
def dropbox_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Dropbox user settings.
    """
    serializer = DropboxSerializer(user_settings=auth.user.get_addon('dropbox'))
    return serializer.serialized_user_settings
