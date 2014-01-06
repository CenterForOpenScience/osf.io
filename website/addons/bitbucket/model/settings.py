"""

"""

import json

from framework import fields

from website.addons.base import AddonSettingsBase

from ..api import Bitbucket


class AddonBitbucketSettings(AddonSettingsBase):

    url = fields.StringField()
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

    def render_widget(self):
        if self.user and self.repo:
            return '''
                <div
                    class="bitbucket-widget"
                    data-repo="{short_url}"
                ></div>
            '''.format(
                short_url=self.short_url
            )

    def render_tab(self):
        return {
            'href': '{0}bitbucket/'.format(self.node.url),
            'text': 'Bitbucket',
        }

    def meta_json(self):
        return json.dumps({
            'bitbucket_user': self.user,
            'bitbucket_repo': self.repo,
            'bitbucket_code': self.oauth_access_token is not None,
            'bitbucket_oauth_user': self.oauth_osf_user.fullname
                                    if self.oauth_osf_user
                                    else '',
        })
