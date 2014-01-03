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

    def before_page_load(self, node, user):
        """

        :param Node node:
        :param User user:

        """
        # Quit if not configured
        if self.user is None or self.repo is None:
            return

        connect = GitHub.from_settings(self)
        repo = connect.repo(self.user, self.repo)

        # Quit if request failed
        if repo is None:
            return

        node_permissions = 'public' if node.is_public else 'private'
        repo_permissions = 'private' if repo['private'] else 'public'
        if repo_permissions != node_permissions:
            push_status_message(
                'This {category} is {node_perm}, but GitHub add-on '
                '{user} / {repo} is {repo_perm}.'.format(
                    category=node.project_or_component,
                    node_perm=node_permissions,
                    repo_perm=repo_permissions,
                    user=self.user,
                    repo=self.repo,
                )
            )

    def before_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:

        """
        if self.oauth_osf_user and self.oauth_osf_user == removed:
            return (
                'The GitHub add-on for this {category} is authenticated '
                'by {user}. Removing this user will also remove write access '
                'to GitHub unless another contributor re-authenticates.'
            ).format(
                category=node.project_or_component,
                user=removed.fullname,
            )

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

    def after_set_permissions(self, node, permissions):
        """

        :param Node node:
        :param str permissions:

        """
        connect = GitHub.from_settings(self)

        data = connect.set_privacy(
            self.user, self.repo, permissions == 'private'
        )
        if data is None or 'errors' in data:
            repo = connect.repo(self.user, self.repo)
            if repo is not None:
                current_privacy = 'private' if repo['private'] else 'public'
            else:
                current_privacy = 'unknown'
            push_status_message(
                'Could not set privacy for repo {user}::{repo}. '
                'Current privacy status is {perm}.'.format(
                    user=self.user,
                    repo=self.repo,
                    perm=current_privacy,
                )
            )
        else:
            push_status_message(
                'GitHub repo {user}::{repo} made {perm}.'.format(
                    user=self.user,
                    repo=self.repo,
                    perm=permissions,
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
        clone.registered = True

        clone.save()
