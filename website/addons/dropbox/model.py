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


class DropboxUserSettings(AddonUserSettingsBase):

    dropbox_id = fields.StringField()
    access_token = fields.StringField()

    def to_json(self, user):
        rv = super(DropboxUserSettings, self).to_json(user)
        rv['has_auth'] = self.has_auth
        return rv

    @property
    def has_auth(self):
        return bool(self.access_key)

    def revoke_auth(self):
        pass  # TODO Finish me

    def delete(self, save=True):
        pass  # TODO Finish me


# TODO Am I needed?
class DropboxNodeSettings(AddonNodeSettingsBase):

    user_settings = fields.ForeignField(
        'dropboxusersettings', backref='authorized'
    )

    def delete(self, save=True):
        super(DropboxNodeSettings, self).delete(save=False)
        if save:
            self.save()

    def to_json(self, user):
        rv = super(DropboxNodeSettings, self).to_json(user)
        return rv

    @property
    def is_registration(self):
        pass

    @property
    def has_auth(self):
        pass
