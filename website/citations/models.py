# -*- coding: utf-8 -*-

import datetime

from modularodm import fields

from framework.auth import Auth
from framework.mongo import StoredObject
from website.addons.base import AddonOAuthNodeSettingsBase

class AddonCitationsNodeSettings(AddonOAuthNodeSettingsBase):

    def serialize_waterbutler_settings(self, *args, **kwargs):
        # required by superclass, not actually used
        pass

    def serialize_waterbutler_credentials(self, *args, **kwargs):
        # required by superclass, not actually used
        pass

    def create_waterbutler_log(self, *args, **kwargs):
        # required by superclass, not actually used
        pass

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = self.oauth_provider(account=self.external_account)
        return self._api

    @property
    def complete(self):
        """Boolean indication of addon completeness"""
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.list_id},
        ))

    @property
    def root_folder(self):
        """Serialized representation of root folder"""
        return self.serializer.serialized_root_folder

    @property
    def folder_id(self):
        return self.list_id

    @property
    def folder_name(self):
        return self.fetch_folder_name

    @property
    def folder_path(self):
        return self.fetch_folder_name

    @property
    def fetch_folder_name(self):
        """Returns a displayable folder name"""
        if self.list_id is None:
            return ''
        elif self.list_id == 'ROOT':
            return 'All Documents'
        else:
            return self._fetch_folder_name

    def clear_settings(self):
        """Clears selected folder configuration"""
        self.list_id = None

    def set_auth(self, *args, **kwargs):
        """Connect the node addon to a user's external account.

        This method also adds the permission to use the account in the user's
        addon settings.
        """
        self.list_id = None
        self.save()

        return super(AddonCitationsNodeSettings, self).set_auth(*args, **kwargs)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        if add_log:
            self.owner.add_log(
                '{0}_node_deauthorized'.format(self.provider_name),
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                },
                auth=auth,
            )

        self.clear_settings()
        self.clear_auth()
        self.save()

    def after_delete(self, node=None, user=None):
        self.deauthorize(Auth(user=user), add_log=True)

    def on_delete(self):
        self.deauthorize(add_log=False)


class CitationStyle(StoredObject):
    """Persistent representation of a CSL style.

    These are parsed from .csl files, so that metadata fields can be indexed.
    """

    # The name of the citation file, sans extension
    _id = fields.StringField(primary=True)

    # The full title of the style
    title = fields.StringField(required=True)

    # Datetime the file was last parsed
    date_parsed = fields.DateTimeField(default=datetime.datetime.utcnow,
                                       required=True)

    short_title = fields.StringField(required=False)
    summary = fields.StringField(required=False)

    def to_json(self):
        return {
            'id': self._id,
            'title': self.title,
            'short_title': self.short_title,
            'summary': self.summary,
        }
