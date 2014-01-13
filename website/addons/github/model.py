"""

"""

import os
import urlparse

from framework import fields

from website import settings
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import AddonError

from . import settings as github_settings
from .api import GitHub


class AddonGitHubUserSettings(AddonUserSettingsBase):

    oauth_state = fields.StringField()
    oauth_access_token = fields.StringField()
    oauth_token_type = fields.StringField()

    @property
    def has_auth(self):
        return self.oauth_access_token is not None

    def to_json(self, user):
        rv = super(AddonGitHubUserSettings, self).to_json(user)
        rv.update({
            'authorized': self.has_auth,
        })
        return rv

class AddonGitHubNodeSettings(AddonNodeSettingsBase):

    user = fields.StringField()
    repo = fields.StringField()
    hook_id = fields.StringField()

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
        rv = super(AddonGitHubNodeSettings, self).to_json(user)
        rv.update({
            'github_user': self.user or '',
            'github_repo': self.repo or '',
            'user_has_authorization': github_user and github_user.has_auth,
        })
        if self.user_settings and self.user_settings.has_auth:
            rv.update({
                'authorized_user': self.user_settings.owner.fullname,
                'disabled': user != self.user_settings.owner,
            })
        return rv

    #############
    # Callbacks #
    #############

    def before_page_load(self, node):
        """

        :param Node node:
        :return str: Alert message

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
            return (
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
        :return str: Alert message

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
        :return str: Alert message

        """
        if self.user_settings and self.user_settings.owner == removed:

            # Delete OAuth tokens
            self.user_settings = None
            self.save()

            #
            return (
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
        :return str: Alert message

        """
        if not github_settings.SET_PRIVACY:
            return

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
            return (
                'Could not set privacy for repo {user}::{repo}. '
                'Current privacy status is {perm}.'.format(
                    user=self.user,
                    repo=self.repo,
                    perm=current_privacy,
                )
            )

        return (
            'GitHub repo {user}::{repo} made {perm}.'.format(
                user=self.user,
                repo=self.repo,
                perm=permissions,
            )
        )

    def after_fork(self, node, fork, user, save=True):
        """

        :param Node node: Original node
        :param Node fork: Forked node
        :param User user: User creating fork
        :param bool save: Save settings after callback
        :return tuple: Tuple of cloned settings and alert message

        """
        clone, _ = super(AddonGitHubNodeSettings, self).after_fork(
            node, fork, user, save=False
        )

        # Copy authentication if authenticated by forking user
        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = (
                'GitHub authorization copied to forked {cat}.'
            ).format(
                cat=fork.project_or_component,
            )
        else:
            message = (
                'GitHub authorization not copied to forked {cat}. You may '
                'authorize this fork on the <a href={url}>Settings</a> '
                'page.'
            ).format(
                cat=fork.project_or_component,
                url=fork.url + 'settings/'
            )

        if save:
            clone.save()

        return clone, message

    def after_register(self, node, registration, user, save=True):
        """

        :param Node node: Original node
        :param Node registration: Registered node
        :param User user: User creating registration
        :param bool save: Save settings after callback
        :return tuple: Tuple of cloned settings and alert message

        """
        clone, message = super(AddonGitHubNodeSettings, self).after_register(
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

        if save:
            clone.save()

        return clone, message

    #########
    # Hooks #
    #########

    def add_hook(self, save=True):

        if self.user_settings:
            connect = GitHub.from_settings(self.user_settings)
            hook = connect.add_hook(
                self.user, self.repo,
                'web',
                {
                    'url': urlparse.urljoin(
                        github_settings.HOOK_DOMAIN or settings.DOMAIN,
                        os.path.join(
                            self.owner.api_url, 'github', 'hook/'
                        )
                    ),
                    'content_type': 'json',
                }
            )

            if hook:
                self.hook_id = hook['id']
                if save:
                    self.save()

    def delete_hook(self, save=True):
        """

        :return bool: Hook was deleted

        """
        if self.user_settings and self.hook_id:
            connect = GitHub.from_settings(self.user_settings)
            response = connect.delete_hook(self.user, self.repo, self.hook_id)
            if response:
                self.hook_id = None
                if save:
                    self.save()
                return True
        return False
