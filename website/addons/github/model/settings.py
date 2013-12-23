"""

"""

import os
import json

from framework import fields
from website.addons.base import AddonSettingsBase

class AddonGitHubSettings(AddonSettingsBase):

    url = fields.StringField()
    user = fields.StringField()
    repo = fields.StringField()

    repo_json = fields.DictionaryField()
    branch_json = fields.DictionaryField()
    commit_json = fields.DictionaryField()

    registered = fields.DictionaryField()

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
        })

    def register(self):

        self._branches(force=True)
        for branch in self.branch_json:
            self._tree(sha=branch['commit']['sha'], force=True)
