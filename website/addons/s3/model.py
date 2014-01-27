'''
Created on Jan 7, 2014

@author: seto
'''
"""

"""

import json

from framework import fields

from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase


class AddonS3UserSettings(AddonUserSettingsBase):

    access_key = fields.StringField()
    secret_key = fields.StringField()

    def to_json(self, user):
        rv = super(AddonS3UserSettings, self).to_json(user)
        rv.update({
            'access_key': self.access_key,
            'secret_key': self.secret_key,
            'user_has_auth': True if self.access_key and self.secret_key else False,
        })
        return rv


class AddonS3NodeSettings(AddonNodeSettingsBase):

    bucket = fields.StringField()
    node_access_key = fields.StringField()
    node_secret_key = fields.StringField()

    # TODO Considering removing node_ in naming
    def to_json(self, user):

        rv = super(AddonS3NodeSettings, self).to_json(user)
        s3_user_settings = user.get_addon('s3')

        rv.update({
            'bucket': self.bucket or '',
            'has_bucket': self.bucket is not None,
            'access_key': self.node_access_key or '',
            'secret_key': self.node_secret_key or '',
            'user_has_auth': False,
            'node_auth': True if self.node_access_key and self.node_secret_key else False
        })
        if s3_user_settings:
            rv['user_has_auth'] = True if s3_user_settings.user_has_auth else False

        return rv

    @property
    def node_auth(self):
        return True if self.node_access_key and self.node_secret_key else False
