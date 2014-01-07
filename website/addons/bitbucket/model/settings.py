"""

"""

from framework import fields
from website.addons.base import AddonSettingsBase


class AddonBitbucketSettings(AddonSettingsBase):

    user = fields.StringField()
    repo = fields.StringField()

    oauth_osf_user = fields.ForeignField('user', backref='authorized')
    oauth_request_token = fields.StringField()
    oauth_request_token_secret = fields.StringField()
    oauth_access_token = fields.StringField()
    oauth_access_token_secret = fields.StringField()

    registration_data = fields.DictionaryField()

    @property
    def short_url(self):
        return '/'.join([self.user, self.repo])

    # TODO: Move to views
    def to_json(self):
        return {
            'bitbucket_user': self.user,
            'bitbucket_repo': self.repo,
            'bitbucket_code': self.oauth_access_token is not None,
            'bitbucket_oauth_user': self.oauth_osf_user.fullname
                                    if self.oauth_osf_user
                                    else '',
        }
