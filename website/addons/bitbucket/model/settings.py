"""

"""

from framework import fields
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase


class AddonBitbucketUserSettings(AddonUserSettingsBase):

    oauth_request_token = fields.StringField()
    oauth_request_token_secret = fields.StringField()
    oauth_access_token = fields.StringField()
    oauth_access_token_secret = fields.StringField()


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
        rv = {
            'bitbucket_user': self.user,
            'bitbucket_repo': self.repo,
            'bitbucket_has_user_authentication': bitbucket_user is not None,
        }
        settings = self.user_settings
        if settings:
            rv.update({
                'bitbucket_has_authentication': settings.oauth_access_token is not None,
                'bitbucket_authenticated_user': settings.owner.fullname,
            })
        return rv