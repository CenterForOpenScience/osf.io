"""

"""

from framework import fields
from framework.status import push_status_message

from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, AddonError

from ..api import GitHub


class AddonGitHubUserSettings(AddonUserSettingsBase):

    oauth_state = fields.StringField()
    oauth_access_token = fields.StringField()
    oauth_token_type = fields.StringField()


class AddonGitHubNodeSettings(AddonNodeSettingsBase):

    user = fields.StringField()
    repo = fields.StringField()

    user_settings = fields.ForeignField(
        'addongithubusersettings', backref='authorized'
    )

    registration_data = fields.DictionaryField()

    @property
    def short_url(self):
        if self.user and self.repo:
            return '/'.join([self.user, self.repo])

    def to_json(self, user):
        github_user = user.get_addon('github')
        rv = {
            'github_user': self.user,
            'github_repo': self.repo,
            'github_has_user_authentication': github_user is not None,
        }
        settings = self.user_settings
        if settings:
            rv.update({
                'github_has_authentication': settings.oauth_access_token is not None,
                'github_authenticated_user': settings.owner.fullname,
            })
        return rv

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

        # Quit if no user authorization
        if self.user_settings is None:
            return
        connect = GitHub.from_settings(self.user_settings)
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

    # TODO: Rename to before_remove_contributor_message
    def before_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:

        """
        if self.user_settings and self.user_settings.owner == removed:
            return (
                'The GitHub add-on for this {category} is authenticated '
                'by {user}. Removing this user will also remove write access '
                'to GitHub unless another contributor re-authenticates. You '
                'can download the contents of this repository before removing '
                'this contributor <a href="{url}">here</a>.'
            ).format(
                category=node.project_or_component,
                user=removed.fullname,
                url=node.api_url + 'github/tarball/'
            )

    def after_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:

        """
        if self.user_settings and self.user_settings.owner == removed:

            # Delete OAuth tokens
            self.user_settings = None
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
        connect = GitHub.from_settings(self.user_settings)

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


    def after_fork(self, node, fork, user, save=True):
        """

        :param Node node:
        :param Node fork:
        :param User user:
        :param bool save:
        :return AddonGitHubNodeSettings:

        """
        clone = super(AddonGitHubNodeSettings, self).after_fork(
            node, fork, user, save=False
        )

        # Copy authentication if authenticated by forking user
        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings

        if save:
            clone.save()

        return clone

    def after_register(self, node, registration, user, save=True):
        """

        :param Node node:
        :param Node registration:
        :param User user:
        :param bool save:
        :return AddonGitHubNodeSettings:

        """
        clone = super(AddonGitHubNodeSettings, self).after_register(
            node, registration, user, save=False
        )

        # Copy foreign fields from current add-on
        clone.user_settings = self.user_settings

        # Store current branch data
        connect = GitHub.from_settings(self.user_settings)
        branches = connect.branches(self.user, self.repo)
        if branches is None:
            raise AddonError('Could not fetch repo branches.')
        clone.registration_data['branches'] = branches
        clone.registered = True

        if save:
            clone.save()

        return clone
