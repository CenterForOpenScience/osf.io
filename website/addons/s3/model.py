'''
Created on Jan 7, 2014

@author: seto
'''
"""

"""

import json

from framework import fields

from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, AddonError


class AddonS3UserSettings(AddonUserSettingsBase):

    access_key = fields.StringField()
    secret_key = fields.StringField()
    user_has_auth = fields.StringField()

    def to_json(self, user):
        rv = super(AddonS3UserSettings, self).to_json(user)
        rv.update({
            'access_key': self.access_key,
            'secret_key': self.secret_key,
            'user_has_auth': True if self.access_key and self.secret_key else False,
            })
        return rv

class AddonS3NodeSettings(AddonNodeSettingsBase):

    s3_bucket = fields.StringField()
    s3_node_access_key = fields.StringField()
    s3_node_secret_key = fields.StringField()

    #TODO Change the naming here its kinda redundant and stupid
    def to_json(self, user):

        rv = super(AddonS3NodeSettings, self).to_json(user)
        s3_user_settings = user.get_addon('s3')

        rv.update({
            's3_bucket': self.s3_bucket or '',
            'has_bucket': self.s3_bucket is not None,
            'access_key': self.s3_node_access_key or '',
            'secret_key': self.s3_node_secret_key or '',
            'user_has_auth': False,
            'node_auth': True if self.s3_node_access_key and self.s3_node_secret_key else False
        })
        if s3_user_settings:
            rv['user_has_auth'] =  True if s3_user_settings.user_has_auth else False

        return rv

    @property
    def node_auth(self):
        return True if self.s3_node_access_key and self.s3_node_secret_key else False
