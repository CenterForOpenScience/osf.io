"""

"""

import json

from framework import fields
from framework.status import push_status_message

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

    #############
    # Callbacks #
    #############

    def after_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:

        """
        if self.oauth_osf_user and self.oauth_osf_user == removed:

            #
            self.oauth_osf_user = None
            self.oauth_access_token = None
            self.save()

            #
            push_status_message(
                'Because the GitHub add-on for this project was authenticated '
                'by {user}, authentication information has been deleted. You '
                'can re-authenticate on the <a href="{url}settings/">'
                'Settings</a> page.'.format(
                    user=removed.fullname,
                    url=node.url,
                )
            )

    def after_fork(self, node, fork, user):
        """

        :param Node node:
        :param Node fork:
        :param User user:

        """
        clone = self.clone()

        # Copy foreign fields from current add-on
        clone.node = fork

        # Copy authentication if authenticated by forking user
        if self.oauth_osf_user and self.oauth_osf_user == user:
            clone.oauth_osf_user = user
        else:
            clone.oauth_access_token = None

        clone.save()

    def after_register(self, node, registration, user):
        """

        :param Node node:
        :param Node registration:
        :param User user:

        """
        clone = self.clone()

        # Copy foreign fields from current add-on
        clone.node = registration
        clone.oauth_osf_user = self.oauth_osf_user

        # Store current branch data
        connect = GitHub.from_settings(self)
        branches = connect.branches(self.user, self.repo)
        if branches is None:
            raise AddonError('Could not fetch repo branches.')
        clone.registration_data['branches'] = branches

        clone.save()
