"""

"""

from framework import fields
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase


class AddonBitbucketUserSettings(AddonUserSettingsBase):

    oauth_request_token = fields.StringField()
    oauth_request_token_secret = fields.StringField()
    oauth_access_token = fields.StringField()
    oauth_access_token_secret = fields.StringField()

    @property
    def has_auth(self):
        return (
            self.oauth_access_token is not None and
            self.oauth_access_token_secret is not None
        )


class AddonBitbucketNodeSettings(AddonNodeSettingsBase):

    user = fields.StringField()
    repo = fields.StringField()

    user_settings = fields.ForeignField(
        'addonbitbucketusersettings', backref='authorized'
    )

    registration_data = fields.DictionaryField()

    @property
    def short_url(self):
        return '/'.join([self.user, self.repo])

    def to_json(self, user):
        bitbucket_user = user.get_addon('bitbucket')
        rv = super(AddonBitbucketNodeSettings, self).to_json(user)
        rv.update({
            'addon_name': 'bitbucket',
            'addon_title': 'Bitbucket',
            'bitbucket_user': self.user if self.user else '',
            'bitbucket_repo': self.repo if self.repo else '',
            'user_has_authorization': bitbucket_user and bitbucket_user.has_auth,
        })
        if self.user_settings and self.user_settings.has_auth:
            rv.update({
                'authorized_user': self.user_settings.owner.fullname,
                'disabled': user != self.user_settings.owner,
            })
        return rv
