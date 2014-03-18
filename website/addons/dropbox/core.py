# -*- coding: utf-8 -*-
"""Core functions for the Dropbox addon."""
from dropbox.client import DropboxClient

from framework import db, storage
from framework.mongo import set_up_storage
from website.addons.base import AddonError

from website.addons.dropbox import MODELS
from website.addons.dropbox.model import (DropboxGuidFile,
    DropboxNodeSettings, DropboxUserSettings
)



def get_client(user):
    """Return a :class:`dropbox.client.DropboxClient`, using a user's
    access token.

    :param User user: The user.
    :raises: AddonError if user does not have the Dropbox addon enabled.
    """
    user_settings = user.get_addon('dropbox')
    if not user_settings:
        raise AddonError('User does not have the Dropbox addon enabled.')
    return DropboxClient(user_settings.access_token)


def init_storage():
    set_up_storage(MODELS, storage_class=storage.MongoStorage, db=db)
