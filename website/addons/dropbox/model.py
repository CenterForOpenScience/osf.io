import os

from framework import fields
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, GuidFile

class DropboxGuidFile(GuidFile):

    path = fields.StringField(index=True)

    @property
    def file_url(self):
        if self.path is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('s3', self.path)


class AddonDropboxUserSettings(AddonUserSettingsBase):

    user_id = fields.StringField()
    access_token = fields.StringField()

    def to_json(self, user):
        rv = super(AddonDropboxUserSettings, self).to_json(user)
        rv['has_auth'] = self.has_auth
        return rv

    @property
    def has_auth(self):
        return bool(self.user_id and self.access_key)

    def revoke_auth(self):
        pass  # TODO Finish me

    def delete(self, save=True):
        pass  # TODO Finish me


# TODO Am I needed?
class AddonDropboxNodeSettings(AddonNodeSettingsBase):

    user_settings = fields.ForeignField(
        'addondropboxusersettings', backref='authorized'
    )

    def delete(self, save=True):
        super(AddonDropboxNodeSettings, self).delete(save=False)
        if save:
            self.save()

    def to_json(self, user):
        rv = super(AddonDropboxNodeSettings, self).to_json(user)
        return rv

    @property
    def is_registration(self):
        pass

    @property
    def has_auth(self):
        pass
