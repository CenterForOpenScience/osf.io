# -*- coding: utf-8 -*-
import os
import logging

from modularodm import Q
from modularodm.exceptions import ModularOdmException
from slugify import slugify

from framework import fields
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, GuidFile

from website.addons.dropbox.client import get_client, get_node_addon_client

logger = logging.getLogger(__name__)
debug = logger.debug


class DropboxFile(GuidFile):

    #: Full path to the file, e.g. 'My Pictures/foo.png'
    path = fields.StringField(required=True, index=True)

    #: Stored metadata from the dropbox API
    #: See https://www.dropbox.com/developers/core/docs#metadata
    metadata = fields.DictionaryField(required=False)

    @property
    def url(self):
        """The web url for the file."""
        return self.node.web_url_for('dropbox_view_file', path=self.path)

    @property
    def file_url(self):
        if self.path is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('dropbox', 'files', self.path)

    @property
    def download_url(self):
        return self.node.web_url_for('dropbox_download', path=self.path)

    # TODO(sloria): TEST ME
    def update_metadata(self, client=None, rev=None):
        cl = client or get_node_addon_client(self.node.get_addon('dropbox'))
        debug(cl)
        self.metadata = cl.metadata(self.path, list=False, rev=rev)

    def get_metadata(self, client=None, force=False, rev=None):
        """Gets the file metadata from the Dropbox API (cached)."""
        if force or (not self.metadata):
            self.update_metadata(client=client, rev=rev)
            self.save()
        return self.metadata

    def get_cache_filename(self, client=None, rev=None):
        metadata = self.get_metadata(client=client, rev=rev)
        return "{slug}_{rev}.html".format(slug=slugify(self.path), rev=metadata['rev'])

    @classmethod
    def get_or_create(cls, node, path):
        """Get or create a new file record.
        Return a tuple of the form ``obj, created``
        """
        try:
            new = cls.find_one(
                Q('node', 'eq', node) &
                Q('path', 'eq', path)
            )
            created = False
        except ModularOdmException:
            # Create new
            new = cls(node=node, path=path)
            new.save()
            created = True
        return new, created


class DropboxUserSettings(AddonUserSettingsBase):
    """Stores user-specific dropbox information, including the Oauth access
    token.
    """

    dropbox_id = fields.StringField(required=False)
    access_token = fields.StringField(required=False)
    account_info = fields.DictionaryField(required=False)

    # TODO(sloria): The `user` param in unnecessary for AddonUserSettings
    def to_json(self, user=None):
        """Return a dictionary representation of the user settings.
        The dictionary keys and values will be available as variables in
        dropbox_user_settings.mako.
        """
        output = super(DropboxUserSettings, self).to_json(self.owner)
        output['has_auth'] = self.has_auth
        return output

    @property
    def has_auth(self):
        return bool(self.access_token)

    def update_account_info(self, client=None):
        """Update Dropbox account info by fetching data from the Dropbox API.
        """
        c = client or get_client(self.owner)
        self.account_info = c.account_info()

    def get_account_info(self, client=None, force=False):
        """Gets the account info from the Dropbox API (cached).
        """
        if force or (not self.account_info):
            self.update_account_info(client=client)
            self.save()
        return self.account_info

    def clear_auth(self):
        self.dropbox_id = None
        self.access_token = None
        return self

    def delete(self):
        super(DropboxUserSettings, self).delete()
        self.clear_auth()
        for node_settings in self.dropboxnodesettings__authorized:
            node_settings.delete(save=False)
            node_settings.user_settings = None
            node_settings.save()


class DropboxNodeSettings(AddonNodeSettingsBase):

    user_settings = fields.ForeignField(
        'dropboxusersettings', backref='authorized'
    )

    folder = fields.StringField(default='')

    @property
    def has_auth(self):
        return bool(self.user_settings and self.user_settings.has_auth)

    def deauthorize(self, auth):
        node = self.owner
        folder = self.folder
        self.user_settings = None
        self.folder = None
        self.owner.add_log(
            action='dropbox_node_deauthorized',
            params={
                'project': node.parent_id,
                'node': node._id,
                'folder': folder
            },
            auth=auth,
        )
