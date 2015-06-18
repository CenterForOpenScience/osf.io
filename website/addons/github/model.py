# -*- coding: utf-8 -*-

import os
import urlparse

import pymongo
from github3 import GitHubError
from modularodm import fields

from framework.auth import Auth

from website import settings
from website.addons.base import exceptions
from website.addons.base import AddonOAuthNodeSettingsBase
from website.addons.base import AddonOAuthUserSettingsBase
from website.addons.base import GuidFile

from website.addons.github import utils
from website.addons.github.api import GitHub
from website.addons.github import settings as github_settings
from website.addons.github import serializer
from website.addons.github.exceptions import ApiError, NotFoundError, TooBigToRenderError

from website.oauth.models import ExternalProvider
from .serializer import GitHubSerializer


hook_domain = github_settings.HOOK_DOMAIN or settings.DOMAIN


class GithubGuidFile(GuidFile):
    __indices__ = [
        {
            'key_or_list': [
                ('node', pymongo.ASCENDING),
                ('path', pymongo.ASCENDING),
            ],
            'unique': True,
        }
    ]

    path = fields.StringField(index=True)

    def maybe_set_version(self, **kwargs):
        # branches are always required for file requests, if not specified
        # file server will assume default branch. e.g. master or develop
        if not kwargs.get('ref'):
            kwargs['ref'] = kwargs.pop('branch', None)
        super(GithubGuidFile, self).maybe_set_version(**kwargs)

    @property
    def waterbutler_path(self):
        return self.path

    @property
    def provider(self):
        return 'github'

    @property
    def version_identifier(self):
        return 'ref'

    @property
    def unique_identifier(self):
        return self._metadata_cache['extra']['fileSha']

    @property
    def name(self):
        return os.path.split(self.path)[1]

    @property
    def extra(self):
        if not self._metadata_cache:
            return {}

        return {
            'sha': self._metadata_cache['extra']['fileSha'],
        }

    def _exception_from_response(self, response):
        try:
            if response.json()['errors'][0]['code'] == 'too_large':
                raise TooBigToRenderError(self)
        except (KeyError, IndexError):
            pass

        super(GithubGuidFile, self)._exception_from_response(response)

#
class GitHubProvider(ExternalProvider):
    name = "GitHub"
    short_name = "github"

    client_id = github_settings.CLIENT_ID
    client_secret = github_settings.CLIENT_SECRET

    auth_url_base = 'https://github.com/login/oauth/authorize'
    callback_url = 'https://github.com/login/oauth/access_token'
    default_scopes = github_settings.SCOPE

    _client = None

    @property
    def api_error_classes(self):
        return GitHubError

    def handle_callback(self, response):
        client = self.client(response)

        return {
            'display_name': client.user().name,
            'provider_id': client.user().id,
            'profile_url': client.user().html_url,
        }

    def client(self, credentials):
        """An API session with GitHub"""
        if not self._client:
            self._client = GitHub(credentials['access_token'])
        return self._client


class GitHubUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = GitHubProvider
    serializer = serializer.GitHubSerializer


class GitHubNodeSettings(AddonOAuthNodeSettingsBase):

    oauth_provider = GitHubProvider
    serializer = GitHubSerializer

    user = fields.StringField()
    repo = fields.StringField()
    hook_id = fields.StringField()
    hook_secret = fields.StringField()

    _api = None

    @property
    def api(self):
        """Authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = GitHubProvider()
            self._api.account = self.external_account
        return self._api

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
        ))

    def find_or_create_file_guid(self, path):
        return GithubGuidFile.get_or_create(node=self.owner, path=path)

    @property
    def provider_name(self):
        return 'github'

    @property
    def is_private(self):
        connection = GitHub.from_settings(self.api.account)
        return connection.repo(user=self.user, repo=self.repo).private

    def set_auth(self, *args, **kwargs):
        self.repo = None
        return super(GitHubNodeSettings, self).set_auth(*args, **kwargs)

    def clear_auth(self):
        self.repo = None
        return super(GitHubNodeSettings, self).clear_auth()

    def delete(self, save=False):
        super(GitHubNodeSettings, self).delete(save=False)
        self.deauthorize(save=False, log=False)
        if save:
            self.save()

    def serialize_waterbutler_credentials(self):
        if not self.complete or not self.repo:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.api.account.oauth_key}

    def serialize_waterbutler_settings(self):
        if not self.complete:
            raise exceptions.AddonError('Repo is not configured')
        return {
            'owner': self.user,
            'repo': self.repo,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        path = metadata['path']

        url = self.owner.web_url_for(
            'addon_view_or_download_file', path=path, provider='github')

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

        connect = GitHub.from_settings(self.api.account)

        try:
            repo = connect.repo(self.user, self.repo)
        except (ApiError, GitHubError):
            return

        node_permissions = 'public' if node.is_public else 'private'
        repo_permissions = 'private' if repo.private else 'public'
        if repo_permissions != node_permissions:
            message = (
                'Warnings: This OSF {category} is {node_perm}, but the GitHub '
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
                    '<a href="https://github.com/{user}/{repo}/">here</a>.'
                ).format(
                    user=self.user,
                    repo=self.repo,
                )
            messages.append(message)
            return messages

    def after_set_privacy(self, node, permissions):
        """

        :param Node node:
        :param str permissions:
        :return str: Alert message

        """
        if not github_settings.SET_PRIVACY:
            return

        connect = GitHub.from_settings(self.api.account)

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

    def after_fork(self, node, fork, user, save=True):
        """
        :param Node node: Original node
        :param Node fork: Forked node
        :param User user: User creating fork
        :param bool save: Save settings after callback
        :return tuple: Tuple of cloned settings and alert message

        """
        clone, _ = super(GitHubNodeSettings, self).after_fork(
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

    def before_register(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.has_auth:
            return (
                u'The contents of GitHub add-ons cannot be registered at this time; '
                u'the GitHub repository linked to this {category} will not be included '
                u'as part of this registration.'
            ).format(**locals())

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

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), log=True, save=True)

    #########
    # Hooks #
    #########

    # TODO: Should Events be added here?
    # TODO: Move hook logic to service
    def add_hook(self, save=True):

        if self.user_settings:
            connect = GitHub.from_settings(self.api.account)
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
            connection = GitHub.from_settings(self.api.account)
            try:
                response = connection.delete_hook(
                    self.user, self.repo, self.hook_id)
            except (GitHubError, NotFoundError):
                return False
            if response:
                self.hook_id = None
                if save:
                    self.save()
                return True
        return False

    selected_folder_name = repo
