import os

from framework import fields
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, GuidFile


class DropboxGuidFile(GuidFile):

    path = fields.StringField(index=True)

    @property
    def file_url(self):
        if self.path is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('dropbox', self.path)


class DropboxUserSettings(AddonUserSettingsBase):

    dropbox_id = fields.StringField()
    access_token = fields.StringField()

    def to_json(self, user):
        output = super(DropboxUserSettings, self).to_json(user)
        output['has_auth'] = self.has_auth
        return output

    @property
    def has_auth(self):
        return bool(self.access_token)

    def clear_auth(self):
        self.dropbox_id = None
        self.access_token = None
        return self

    def delete(self):
        super(DropboxUserSettings, self).delete()
        self.clear_auth()
        for node_settings in self.dropboxnodesettings__authorized:
            node_settings.delete(save=False)
            node_settings.user_settings = None
            node_settings.save()


class DropboxNodeSettings(AddonNodeSettingsBase):

    user_settings = fields.ForeignField(
        'dropboxusersettings', backref='authorized'
    )

    folder = fields.StringField()

    @property
    def has_auth(self):
        return True  # TODO Fix me
        #return self.user_setttings and self.user_setttings.has_auth

    def delete(self, save=True):
        super(DropboxNodeSettings, self).delete(save=False)
        if save:
            self.save()

    def to_json(self, user):
        ret = super(DropboxNodeSettings, self).to_json(user)
        ret.update({
            'folder': self.folder or '',
            'node_has_auth': self.has_auth,
            'is_owner': False,
            'user_has_auth': True,
            'owner_url': '',
            'owner': 'JimBob',
        })

        return ret
