# -*- coding: utf-8 -*-

import datetime

from modularodm import fields

from framework.mongo import StoredObject
from website.addons.base import AddonOAuthNodeSettingsBase

class AddonCitationsNodeSettings(AddonOAuthNodeSettingsBase):

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = self.oauth_provider(account=self.external_account)
        return self._api

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.list_id},
        ))

    @property
    def root_folder(self):
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

    def clear_auth(self):
        self.list_id = None
        return super(AddonCitationsNodeSettings, self).clear_auth()

    def set_auth(self, *args, **kwargs):
        self.list_id = None
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

        self.clear_auth()
        self.save()


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
