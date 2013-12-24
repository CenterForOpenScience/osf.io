"""

"""

import json

from framework import fields
from website.addons.base import AddonSettingsBase, AddonError

from ..api import GitHub

class AddonGitHubSettings(AddonSettingsBase):

    SHORT_NAME = 'github'

    url = fields.StringField()
    user = fields.StringField()
    repo = fields.StringField()

    oauth_osf_user = fields.ForeignField('user', backref='authorized')
    oauth_state = fields.StringField()
    oauth_access_token = fields.StringField()

    registration_data = fields.DictionaryField()

    @property
    def short_url(self):
        return '/'.join([self.user, self.repo])

    def render_widget(self):
        if self.user and self.repo:
            return '''
                <div
                    class="github-widget"
                    data-repo="{short_url}"
                ></div>
            '''.format(
                short_url=self.short_url
            )

    def render_tab(self):
        return '''
            <a href="{url}github/">GitHub</a>
        '''.format(
            url=self.node.url,
        )

    def meta_json(self):
        return json.dumps({
            'github_user': self.user,
            'github_repo': self.repo,
            'github_code': self.oauth_access_token is not None,
            'github_oauth_user': self.oauth_osf_user.fullname
                                 if self.oauth_osf_user
                                 else '',
        })

    def register(self, save=True):
        """

        """
        connect = GitHub.from_settings(self)
        branches = connect.branches(self.user, self.repo)
        if branches is None:
            raise AddonError('Could not fetch repo branches.')

        self.registration_data['branches'] = branches

        super(AddonGitHubSettings, self).register(save=False)

        if save:
            self.save()
