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
            'user_has_auth' : self.user_has_auth,
            'show_submit' : True,
            })
        return rv

class AddonS3NodeSettings(AddonNodeSettingsBase):

    s3_bucket = fields.StringField()
    s3_node_access_key = fields.StringField()
    s3_node_secret_key = fields.StringField()
    node_auth = fields.StringField()

    user_settings = fields.ForeignField(
        'addons3usersettings', backref='authorized'
    )

    def to_json(self, user):
        rv = super(AddonS3NodeSettings, self).to_json(user)
        rv.update({
            's3_bucket': self.s3_bucket or '',
            'has_bucket': self.s3_bucket is not None,
            'node_auth': self.node_auth or 0,
            'access_key': self.s3_node_access_key or '',
            'secret_key': self.s3_node_secret_key or ''
        })
        if self.user_settings:
            rv.update({
            'user_has_auth': self.user_settings.user_has_auth or 0,
        })

        return rv
