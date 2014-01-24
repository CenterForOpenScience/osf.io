"""

"""

from framework import fields
from website.addons.base import AddonNodeSettingsBase, AddonUserSettingsBase


class AddonDataverseUserSettings(AddonUserSettingsBase):

    dataverse_username = fields.StringField()
    dataverse_password = fields.StringField()
    connection = fields.ForeignField('DvnConnection')

    def to_json(self, user):
        rv = super(AddonDataverseUserSettings, self).to_json(user)
        rv.update({
            'authorized': self.dataverse_username is not None,
            'authorized_dataverse_user': self.dataverse_username if self.dataverse_username else '',
            'show_submit': False,
        })
        return rv


class AddonDataverseNodeSettings(AddonNodeSettingsBase):

    dataverse_url = fields.StringField()
    dataverse = fields.StringField()
    study = fields.StringField()
    user = fields.StringField()

    def to_json(self, user):
        rv = super(AddonDataverseNodeSettings, self).to_json(user)
        rv.update({
            'dataverse_url': self.dataverse_url or '',
            'dataverse': self.dataverse or '',
            'study': self.study or '',
        })
        return rv
