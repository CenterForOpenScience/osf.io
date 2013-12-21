"""

"""

import os
import json
import requests

from framework import fields
from website.addons.base import AddonSettingsBase

API_URL = 'https://api.github.com/'

GITHUB_USER = 'jmcarp'
GITHUB_TOKEN = '15bbe00083ffa522f55dc8079c017f795988f92c'

GITHUB_AUTH = (
    GITHUB_USER,
    GITHUB_TOKEN,
)

type_map = {
    'tree': 'folder',
    'blob': 'file',
}

def tree_to_hgrid(tree, repo_name):

    grid = []

    repo = {
        'uid': '__repo__',
        'name': 'GitHub :: {0}'.format(repo_name),
        'parent_uid': 'null',
        'url': '',
        'type': 'folder',
    }

    grid.append(repo)

    for item in tree:

        split = os.path.split(item['path'])

        row = {
            'uid': item['path'],
            'name': split[1],
            'parent_uid': split[0] if split[0] else '__repo__',
            'url': item['url'],
            'type': type_map[item['type']],
        }

        grid.append(row)

    return grid

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

    def _branches(self, force=False):

        req = requests.get(
            os.path.join(API_URL, 'repos', self.user, self.repo, 'branches'),
            auth=GITHUB_AUTH,
        )
        if req.status_code == 200:
            return req.json()

    def _repo(self, force=False):

        req = requests.get(
            os.path.join(API_URL, 'repos', self.user, self.repo),
            auth=GITHUB_AUTH,
        )
        if req.status_code == 200:
            return req.json()

    #def _last_commit(self):
    #
    #    req = requests.get(
    #        os.path.join(API_URL, 'repos', self.user, self.repo, 'commits'),
    #        params={'per_page': 1},
    #        auth=GITHUB_AUTH,
    #    )
    #    if req.status_code == 200:
    #        return req.json()[0]
    #    return None

    def _file_tree(self, force=False):

        last_commit = self._last_commit()
        if last_commit:
            req = requests.get(
                os.path.join(
                    API_URL, 'repos',self.user, self.repo, 'git', 'trees',
                    last_commit['sha']
                ),
                params={'recursive': 1},
            auth=GITHUB_AUTH,
            )
            if req.status_code == 200:
                return req.json().get('tree', [])
        return None

    def render_tab(self):
        return '''
            <a href="{url}github/">GitHub</a>
        '''.format(
            url=self.node.url,
        )

    def render_page(self):

        file_tree = self._file_tree()
        if file_tree:
            hgrid_data = tree_to_hgrid(file_tree, self.repo)
            return '''
                <div id="gitCrumb"></div>
                <div id="gitGrid"></div>
                <script type="text/javascript">
                    var gridData = {data};
                </script>
            '''.format(
                data=json.dumps(hgrid_data)
            )
        return ''

    def meta_json(self):
        return json.dumps({
            'github_user': self.user,
            'github_repo': self.repo,
        })

    def register(self):

        self._branches(force=True)
        for branch in self.branch_json:
            self._tree(sha=branch['commit']['sha'], force=True)
