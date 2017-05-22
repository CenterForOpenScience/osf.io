# -*- coding: utf-8 -*-


from modularodm import fields

from framework.exceptions import HTTPError

from website.addons.base import (
    AddonOAuthNodeSettingsBase, AddonOAuthUserSettingsBase, exceptions,
)
from website.addons.base import StorageAddonBase

from website.addons.dmptool.serializer import DmptoolSerializer

ROOT_FOLDER_ID = '/'
ROOT_FOLDER_NAME = '/ (Full DMPTool)'


class DmptoolProvider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'Dmptool'
    short_name = 'dmptool'
    serializer = DmptoolSerializer

    def __init__(self, account=None):
        super(DmptoolProvider, self).__init__()
        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )

class AddonDmptoolUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = DmptoolProvider
    serializer = DmptoolSerializer

class AddonDmptoolNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = DmptoolProvider
    serializer = DmptoolSerializer

    folder_id = fields.StringField(default=ROOT_FOLDER_ID)
    folder_name = fields.StringField(default=ROOT_FOLDER_NAME)
    folder_path = fields.StringField(default=ROOT_FOLDER_ID)

    def set_user_auth(self, user_settings):

        # TO DO:  but this function should go away upon switching to use the generic_views found in website/addons/base/
        # https://github.com/CenterForOpenScience/osf.io/pull/4670#discussion_r67694204

        self.user_settings = user_settings
        self.nodelogger.log(action='node_authorized', save=True)

    def set_folder(self, folder_id, auth):

        self.folder_id = str(folder_id)
        self.folder_name = ROOT_FOLDER_NAME
        self.folder_path = ROOT_FOLDER_ID
        self.save()

        if not self.complete:
            self.user_settings.grant_oauth_access(
                node=self.owner,
                external_account=self.external_account,
                metadata={'folder': self.folder_id}
            )
            self.user_settings.save()

        self.nodelogger.log(action='folder_selected', save=True)

    # based on https://github.com/CenterForOpenScience/osf.io/blob/4a5d4e5a887c944174694300c42b399638184722/website/addons/box/model.py#L105-L107
    def fetch_full_folder_path(self):
        # don't know why this would be needed for Evernote

        return self.folder_path

    def fetch_folder_name(self):
        # don't know why this would be needed for Evernote

        return self.folder_name

    def clear_settings(self):
        """
        TO DO: deal with this hack.  For the dmptool, there is no folder per se, just plans.
        """
        self.folder_id = ROOT_FOLDER_ID
        self.folder_name = ROOT_FOLDER_NAME
        self.folder_path = ROOT_FOLDER_ID

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        folder_id = self.folder_id
        self.clear_settings()

        if add_log:
            extra = {'folder_id': folder_id}
            self.nodelogger.log(action='node_deauthorized', extra=extra, save=True)

        self.clear_auth()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        try:
            return {'host': self.external_account.oauth_key,
                    'api_token': self.external_account.oauth_secret}
        except Exception as error:
            raise HTTPError(str(error), data={'message_long': error.message})

    def serialize_waterbutler_settings(self):
        if self.folder_id is None:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder_id}

    # TO DO : may need create_waterbutler_log
    # https://github.com/CenterForOpenScience/osf.io/pull/4670/#discussion_r67736406
