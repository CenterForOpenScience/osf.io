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



class AddonS3NodeSettings(AddonNodeSettingsBase):

    s3_bucket = fields.StringField()
    access_key = fields.StringField()
    secret_key = fields.StringField()

    user_settings = fields.ForeignField(
        'addons3usersettings', backref='authorized'
    )


    def to_json(self, user):
        rv = {
            's3_bucket': self.s3_bucket,
            'access_key': self.access_key,
            'secret_key': self.secret_key
        }
        return rv

    def _get_bucket_list(self, user):
        pass
