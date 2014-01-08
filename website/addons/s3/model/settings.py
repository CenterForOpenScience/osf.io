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

    user_settings = fields.ForeignField(
        'addons3usersettings', backref='authorized'
    )


    def to_json(self, user):
        rv = {
            'bucket': self.s3_bucket
        }
        settings = self.user_settings
        if settings:
            rv.update({
                'access_key': settings.access_key,
                'secret_key': settings.secret_key
            })
        return rv

    def _get_bucket_list(self, user):
        pass
