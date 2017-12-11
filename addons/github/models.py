# -*- coding: utf-8 -*-

import itertools
import os
import urlparse

import markupsafe
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from framework.auth import Auth
from github3 import GitHubError
from osf.models.external import ExternalProvider
from osf.models.files import File, Folder, BaseFileNode
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from website import settings
from addons.base import exceptions
from addons.github import settings as github_settings
from addons.github import utils
from addons.github.api import GitHubClient
from addons.github.exceptions import ApiError, NotFoundError
from addons.github.serializer import GitHubSerializer
from website.util import web_url_for
hook_domain = github_settings.HOOK_DOMAIN or settings.DOMAIN


class GithubFileNode(BaseFileNode):
    _provider = 'github'


class GithubFolder(GithubFileNode, Folder):
    pass


class GithubFile(GithubFileNode, File):
    version_identifier = 'ref'

    @property
    def _hashes(self):
        try:
            return {'fileSha': self.history[-1]['extra']['hashes']['git']}
        except (IndexError, KeyError):
            return None

    def touch(self, auth_header, revision=None, ref=None, branch=None, **kwargs):
        revision = revision or ref or branch
        return super(GithubFile, self).touch(auth_header, revision=revision, **kwargs)


class GitHubProvider(ExternalProvider):
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
            access_token=response['access_token']
        )

        user_info = client.user()

        return {
            'provider_id': str(user_info.id),
            'profile_url': user_info.html_url,
            'display_name': user_info.login
        }


class UserSettings(BaseOAuthUserSettings):
    """Stores user-specific github information
    """
    oauth_provider = GitHubProvider
    serializer = GitHubSerializer

    def revoke_remote_oauth_access(self, external_account):
        """Overrides default behavior during external_account deactivation.

        Tells GitHub to remove the grant for the OSF associated with this account.
        """
        connection = GitHubClient(external_account=external_account)
        try:
            connection.revoke_token()
        except GitHubError:
            pass

    # Required for importing username from social profile configuration page
    # Assumes oldest connected account is primary.
    @property
    def public_id(self):
        gh_accounts = self.owner.external_accounts.filter(provider=self.oauth_provider.short_name)
        if gh_accounts:
            return gh_accounts[0].display_name
        return None


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = GitHubProvider
    serializer = GitHubSerializer

    user = models.TextField(blank=True, null=True)
    repo = models.TextField(blank=True, null=True)
    hook_id = models.TextField(blank=True, null=True)
    hook_secret = models.TextField(blank=True, null=True)
    registration_data = DateTimeAwareJSONField(default=dict, blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def folder_id(self):
        return self.repo or None

    @property
    def folder_name(self):
        if self.complete:
            return '{}/{}'.format(self.user, self.repo)
        return None

    @property
    def folder_path(self):
        return self.repo or None

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

    def clear_settings(self):
        self.user = None
        self.repo = None
        self.hook_id = None
        self.hook_secret = None
        self.registration_data = None

    def deauthorize(self, auth=None, log=True):
        self.delete_hook(save=False)
        self.clear_settings()
        if log:
            self.owner.add_log(
                action='github_node_deauthorized',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                },
                auth=auth,
            )

        self.clear_auth()

    def delete(self, save=False):
        super(NodeSettings, self).delete(save=False)
        self.deauthorize(log=False)
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
        connection = GitHubClient(external_account=self.external_account)
        try:
            return connection.repo(user=self.user, repo=self.repo).private
        except GitHubError:
            return

    # TODO: Delete me and replace with serialize_settings / Knockout
    def to_json(self, user):
        ret = super(NodeSettings, self).to_json(user)
        user_settings = user.get_addon('github')
        ret.update({
            'user_has_auth': user_settings and user_settings.has_auth,
            'is_registration': self.owner.is_registration,
        })
        if self.has_auth:
            valid_credentials = False
            owner = self.user_settings.owner
            connection = GitHubClient(external_account=self.external_account)
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
            if owner == user:
                ret.update({'repo_names': repo_names})
            ret.update({
                'node_has_auth': True,
                'github_user': self.user or '',
                'github_repo': self.repo or '',
                'github_repo_full_name': '{0} / {1}'.format(self.user, self.repo) if (self.user and self.repo) else '',
                'auth_osf_name': owner.fullname,
                'auth_osf_url': owner.url,
                'auth_osf_id': owner._id,
                'github_user_name': self.external_account.display_name,
                'github_user_url': self.external_account.profile_url,
                'is_owner': owner == user,
                'valid_credentials': valid_credentials,
                'addons_url': web_url_for('user_addons'),
                'files_url': self.owner.web_url_for('collect_file_trees')
            })
        return ret

    def serialize_waterbutler_credentials(self):
        if not self.complete or not self.repo:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.external_account.oauth_key}

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

        sha, urls = None, {}
        try:
            sha = metadata['extra']['commit']['sha']
            urls = {
                'view': '{0}?ref={1}'.format(url, sha),
                'download': '{0}?action=download&ref={1}'.format(url, sha)
            }
        except KeyError:
            pass

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

        connect = GitHubClient(external_account=self.external_account)

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
                    category=markupsafe.escape(node.project_or_component),
                    node_perm=markupsafe.escape(node_permissions),
                    repo_perm=markupsafe.escape(repo_permissions),
                    user=markupsafe.escape(self.user),
                    repo=markupsafe.escape(self.repo),
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
        try:
            message = (super(NodeSettings, self).before_remove_contributor_message(node, removed) +
            'You can download the contents of this repository before removing '
            'this contributor <u><a href="{url}">here</a></u>.'.format(
                url=node.api_url + 'github/tarball/'
            ))
        except TypeError:
            # super call returned None due to lack of user auth
            return None
        else:
            return message

    def after_remove_contributor(self, node, removed, auth=None):
        """
        :param Node node:
        :param User removed:
        :return str: Alert message
        """
        if self.user_settings and self.user_settings.owner == removed:

            # Delete OAuth tokens
            self.user_settings = None
            self.save()
            message = (
                u'Because the GitHub add-on for {category} "{title}" was authenticated '
                u'by {user}, authentication information has been deleted.'
            ).format(
                category=markupsafe.escape(node.category_display),
                title=markupsafe.escape(node.title),
                user=markupsafe.escape(removed.fullname)
            )

            if not auth or auth.user != removed:
                url = node.web_url_for('node_setting')
                message += (
                    u' You can re-authenticate on the <u><a href="{url}">Settings</a></u> page.'
                ).format(url=url)
            #
            return message

    def after_fork(self, node, fork, user, save=True):
        """
        :param Node node: Original node
        :param Node fork: Forked node
        :param User user: User creating fork
        :param bool save: Save settings after callback
        :return the cloned settings
        """
        clone = super(NodeSettings, self).after_fork(
            node, fork, user, save=False
        )

        # Copy authentication if authenticated by forking user
        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings

        if save:
            clone.save()

        return clone

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
        self.deauthorize(Auth(user=user), log=True)

    #########
    # Hooks #
    #########

    # TODO: Should Events be added here?
    # TODO: Move hook logic to service
    def add_hook(self, save=True):

        if self.user_settings:
            connect = GitHubClient(external_account=self.external_account)
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
                },
                events=github_settings.HOOK_EVENTS,
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
            connection = GitHubClient(external_account=self.external_account)
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
