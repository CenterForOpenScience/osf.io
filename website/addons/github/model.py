# -*- coding: utf-8 -*-

import os
import urlparse
import itertools

from github3 import GitHubError
from modularodm import fields

from framework.auth import Auth

from website import settings
from website.util import web_url_for
from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.github import utils
from website.addons.github.api import GitHubClient
from website.addons.github.serializer import GitHubSerializer
from website.addons.github import settings as github_settings
from website.addons.github.exceptions import ApiError, NotFoundError
from website.oauth.models import ExternalProvider


hook_domain = github_settings.HOOK_DOMAIN or settings.DOMAIN


class GithHubProvider(ExternalProvider):
    name = 'GitHub'
    short_name = 'github'

    client_id = github_settings.CLIENT_ID
    client_secret = github_settings.CLIENT_SECRET

    auth_url_base = github_settings.OAUTH_AUTHORIZE_URL
    callback_url = github_settings.OAUTH_ACCESS_TOKEN_URL
    default_scopes = github_settings.SCOPE

    def handle_callback(self, response):
        """View called when the OAuth flow is completed. Adds a new GitHubUserSettings
        record to the user and saves the account info.
        """
        client = GitHubClient(
            access_token=response['access_token'],
            token_type=response['token_type']
        )

        user_info = client.user()

        return {
            'provider_id': user_info.id,
            'profile_url': user_info.html_url,
            'display_name': user_info.login
        }


class GitHubUserSettings(AddonOAuthUserSettingsBase):
    """Stores user-specific github information
    """
    oauth_provider = GithHubProvider
    serializer = GitHubSerializer  # TODO


class GitHubNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):

    user = fields.StringField()
    repo = fields.StringField()
    hook_id = fields.StringField()
    hook_secret = fields.StringField()

    user_settings = fields.ForeignField(
        'addongithubusersettings', backref='authorized'
    )

    registration_data = fields.DictionaryField()

    @property
    def folder_name(self):
        return self.repo

    @property
    def has_auth(self):
        return bool(self.user_settings and self.user_settings.has_auth)

    @property
    def complete(self):
        return self.has_auth and self.repo is not None and self.user is not None

    def authorize(self, user_settings, save=False):
        self.user_settings = user_settings
        self.owner.add_log(
            action='github_node_authorized',
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
            },
            auth=Auth(user_settings.owner),
        )
        if save:
            self.save()

    def deauthorize(self, auth=None, log=True, save=False):
        self.delete_hook(save=False)
        self.user, self.repo, self.user_settings = None, None, None
        if log:
            self.owner.add_log(
                action='github_node_deauthorized',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                },
                auth=auth,
            )
        if save:
            self.save()

    def delete(self, save=False):
        super(GitHubNodeSettings, self).delete(save=False)
        self.deauthorize(save=False, log=False)
        if save:
            self.save()

    @property
    def repo_url(self):
        if self.user and self.repo:
            return 'https://github.com/{0}/{1}/'.format(
                self.user, self.repo
            )

    @property
    def short_url(self):
        if self.user and self.repo:
            return '/'.join([self.user, self.repo])

    @property
    def is_private(self):
        connection = GitHubClient.from_settings(self.user_settings)
        return connection.repo(user=self.user, repo=self.repo).private

    # TODO: Delete me and replace with serialize_settings / Knockout
    def to_json(self, user):
        ret = super(GitHubNodeSettings, self).to_json(user)
        user_settings = user.get_addon('github')
        ret.update({
            'user_has_auth': user_settings and user_settings.has_auth,
            'is_registration': self.owner.is_registration,
        })
        if self.user_settings and self.user_settings.has_auth:
            valid_credentials = False
            owner = self.user_settings.owner
            if user_settings and user_settings.owner == owner:
                connection = GitHubClient.from_settings(user_settings)
                # TODO: Fetch repo list client-side
                # Since /user/repos excludes organization repos to which the
                # current user has push access, we have to make extra requests to
                # find them
                valid_credentials = True
                try:
                    repos = itertools.chain.from_iterable((connection.repos(), connection.my_org_repos()))
                    repo_names = [
                        '{0} / {1}'.format(repo.owner.login, repo.name)
                        for repo in repos
                    ]
                except GitHubError:
                    repo_names = []
                    valid_credentials = False
                ret.update({'repo_names': repo_names})
            ret.update({
                'node_has_auth': True,
                'github_user': self.user or '',
                'github_repo': self.repo or '',
                'github_repo_full_name': '{0} / {1}'.format(self.user, self.repo),
                'auth_osf_name': owner.fullname,
                'auth_osf_url': owner.url,
                'auth_osf_id': owner._id,
                'github_user_name': self.user_settings.github_user_name,
                'github_user_url': 'https://github.com/{0}'.format(self.user_settings.github_user_name),
                'is_owner': owner == user,
                'valid_credentials': valid_credentials,
                'addons_url': web_url_for('user_addons'),
            })
        return ret

    def serialize_waterbutler_credentials(self):
        if not self.complete or not self.repo:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.user_settings.oauth_access_token}

    def serialize_waterbutler_settings(self):
        if not self.complete:
            raise exceptions.AddonError('Repo is not configured')
        return {
            'owner': self.user,
            'repo': self.repo,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        path = metadata['path']

        url = self.owner.web_url_for('addon_view_or_download_file', path=path, provider='github')

        if not metadata.get('extra'):
            sha = None
            urls = {}
        else:
            sha = metadata['extra']['commit']['sha']
            urls = {
                'view': '{0}?ref={1}'.format(url, sha),
                'download': '{0}?action=download&ref={1}'.format(url, sha)
            }

        self.owner.add_log(
            'github_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': path,
                'urls': urls,
                'github': {
                    'user': self.user,
                    'repo': self.repo,
                    'sha': sha,
                },
            },
        )

    #############
    # Callbacks #
    #############

    def before_page_load(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message
        """
        messages = []

        # Quit if not contributor
        if not node.is_contributor(user):
            return messages

        # Quit if not configured
        if self.user is None or self.repo is None:
            return messages

        # Quit if no user authorization
        if self.user_settings is None:
            return messages

        connect = GitHubClient.from_settings(self.user_settings)

        try:
            repo = connect.repo(self.user, self.repo)
        except (ApiError, GitHubError):
            return

        node_permissions = 'public' if node.is_public else 'private'
        repo_permissions = 'private' if repo.private else 'public'
        if repo_permissions != node_permissions:
            message = (
                'Warning: This OSF {category} is {node_perm}, but the GitHub '
                'repo {user} / {repo} is {repo_perm}.'.format(
                    category=node.project_or_component,
                    node_perm=node_permissions,
                    repo_perm=repo_permissions,
                    user=self.user,
                    repo=self.repo,
                )
            )
            if repo_permissions == 'private':
                message += (
                    ' Users can view the contents of this private GitHub '
                    'repository through this public project.'
                )
            else:
                message += (
                    ' The files in this GitHub repo can be viewed on GitHub '
                    '<u><a href="https://github.com/{user}/{repo}/">here</a></u>.'
                ).format(
                    user=self.user,
                    repo=self.repo,
                )
            messages.append(message)
            return messages

    def before_remove_contributor_message(self, node, removed):
        """

        :param Node node:
        :param User removed:
        :return str: Alert message

        """
        return (super(GitHubNodeSettings, self).before_remove_contributor_message(node, removed) +
            'You can download the contents of this repository before removing '
            'this contributor <u><a href="{url}">here</a></u>.'.format(
                url=node.api_url + 'github/tarball/'
        ))

    # backwards compatibility -- TODO: is this necessary?
    before_remove_contributor = before_remove_contributor_message

    def after_set_privacy(self, node, permissions):
        """

        :param Node node:
        :param str permissions:
        :return str: Alert message

        """
        if not github_settings.SET_PRIVACY:
            return

        connect = GitHubClient.from_settings(self.user_settings)

        data = connect.set_privacy(
            self.user, self.repo, permissions == 'private'
        )
        if data is None or 'errors' in data:
            repo = connect.repo(self.user, self.repo)
            if repo is not None:
                current_privacy = 'private' if repo.private else 'public'
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

    def before_make_public(self, node):
        try:
            is_private = self.is_private
        except NotFoundError:
            return None
        if is_private:
            return (
                'This {cat} is connected to a private GitHub repository. Users '
                '(other than contributors) will not be able to see the '
                'contents of this repo unless it is made public on GitHub.'
            ).format(
                cat=node.project_or_component,
            )

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), log=True, save=True)

    #########
    # Hooks #
    #########

    # TODO: Should Events be added here?
    # TODO: Move hook logic to service
    def add_hook(self, save=True):

        if self.user_settings:
            connect = GitHubClient.from_settings(self.user_settings)
            secret = utils.make_hook_secret()
            hook = connect.add_hook(
                self.user, self.repo,
                'web',
                {
                    'url': urlparse.urljoin(
                        hook_domain,
                        os.path.join(
                            self.owner.api_url, 'github', 'hook/'
                        )
                    ),
                    'content_type': github_settings.HOOK_CONTENT_TYPE,
                    'secret': secret,
                }
            )

            if hook:
                self.hook_id = hook.id
                self.hook_secret = secret
                if save:
                    self.save()

    def delete_hook(self, save=True):
        """
        :return bool: Hook was deleted
        """
        if self.user_settings and self.hook_id:
            connection = GitHubClient.from_settings(self.user_settings)
            try:
                response = connection.delete_hook(self.user, self.repo, self.hook_id)
            except (GitHubError, NotFoundError):
                return False
            if response:
                self.hook_id = None
                if save:
                    self.save()
                return True
        return False
