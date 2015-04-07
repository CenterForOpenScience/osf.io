# -*- coding: utf-8 -*-

import os
import urlparse
import itertools
import httplib as http

import pymongo
from github3 import GitHubError
from modularodm import fields, Q
from modularodm.exceptions import ModularOdmException

from framework.auth import Auth
from framework.mongo import StoredObject

from website import settings
from website.util import web_url_for
from website.addons.base import GuidFile
from website.addons.base import exceptions
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
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


class GitHubProvider(ExternalProvider):
    name = "GitHub"
    short_name = "github"

    client_id = github_settings.GITHUB_CLIENT_ID
    client_secret = github_settings.GITHUB_CLIENT_SECRET

    auth_url_base = 'https://github.com/login/oauth/authorize'
    callback_url = 'https://github.com/login/oauth/access_token'
    default_scopes = github_settings.SCOPE

    _client = None

    def handle_callback(self, response):
        client = self.get_client(response)
        import ipdb; ipdb.set_trace()
        return {
            'display_name': client.user().name,
            'provider_id': client.user().id,
            'profile_url': client.user().html_url,
        }

    def get_client(self, credentials):
        """An API session with Mendeley"""
        if not self._client:
            self._client = GitHub(credentials['access_token'], 'bearer') #Token Type bearer correct?
        return self._client


class GitHubUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = GitHubProvider
    serializer = serializer.GitHubSerializer


class GitHubNodeSettings(AddonOAuthNodeSettingsBase):

    oauth_provider = GitHubProvider
    serializer = GitHubSerializer

    github_list_id = fields.StringField()
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
            metadata={'folder': self.repo_folder_id}
        ))

    def find_or_create_file_guid(self, path):
        return GithubGuidFile.get_or_create(node=self.owner, path=path)

    # def set_folder(self, folder, auth, add_log=True):
    #     self.repo_folder_id = folder['id']
    #     self.folder_path = folder['path']

    @property
    def provider_name(self):
        return 'github'

    def set_auth(self, *args, **kwargs):
        self.github_list_id = None
        return super(GitHubNodeSettings, self).set_auth(*args, **kwargs)

    def clear_auth(self):
        self.github_list_id = None
        return super(GitHubNodeSettings, self).clear_auth()

    # def set_target_folder(self, folder, auth):
    #     """Configure this addon to point to a GitHub Drive folder
    #     :param dict folder:
    #     :param User user:
    #     """
    #     self.repo_folder_id = folder['id']
    #     self.folder_path = folder['path']
    #     self.repo_folder_name = folder['name']
    #
    #     # Tell the user's addon settings that this node is connecting
    #     self.user_settings.grant_oauth_access(
    #         node=self.owner,
    #         external_account=self.external_account,
    #         metadata={'folder': self.repo_folder_id}
    #     )
    #     self.user_settings.save()
    #
    #     # update this instance
    #     self.save()
    #
    #     self.owner.add_log(
    #         'googlerepo_folder_selected',
    #         params={
    #             'project': self.owner.parent_id,
    #             'node': self.owner._id,
    #             'folder_id': self.repo_folder_id,
    #             'folder_name': self.repo_folder_name,
    #         },
    #         auth=auth,
    #   )

    # # TODO: Delete me and replace with serialize_settings / Knockout
    # def to_json(self, user):
    #     ret = super(GitHubNodeSettings, self).to_json(user)
    #
    #     user_settings = user.get_addon('github')
    #
    #     ret.update({
    #         'repo': self.repo or '',
    #         'has_repo': self.repo is not None,
    #         'user_has_auth': user_settings and user_settings.has_auth,
    #         'node_has_auth': False,
    #         'user_is_owner': (
    #             (self.user_settings and self.user_settings.owner == user) or False
    #         ),
    #         'owner': None,
    #         'repo_names': None,
    #         'is_registration': self.owner.is_registration,
    #     })
    #
    #     if self.user_settings and self.user_settings.has_auth:
    #         owner = self.user_settings.owner
    #         if user_settings and user_settings.owner == owner:
    #             connection = GitHub.from_settings(user_settings)
    #             # TODO: Fetch repo list client-side
    #             # Since /user/repos excludes organization repos to which the
    #             # current user has push access, we have to make extra requests to
    #             # find them
    #             repos = itertools.chain.from_iterable((connection.repos(), connection.my_org_repos()))
    #             repo_names = [
    #                 '{0} / {1}'.format(repo.owner.login, repo.name)
    #                 for repo in repos
    #             ]
    #             ret.update({
    #                 'repo_names': repo_names,
    #             })
    #
    #         ret.update({
    #             'node_has_auth': True,
    #             'github_user': self.user or '',
    #             'github_repo': self.repo or '',
    #             'github_repo_full_name': '{0} / {1}'.format(self.user, self.repo),
    #             'auth_osf_name': owner.fullname,
    #             'auth_osf_url': owner.url,
    #             'auth_osf_id': owner._id,
    #             'github_user_name': self.user_settings.github_user_name,
    #             'github_user_url': 'https://github.com/{0}'.format(self.user_settings.github_user_name),
    #             'is_owner': owner == user,
    #             'owner': self.user_settings.owner.fullname
    #         })
    #     return ret

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

        connect = GitHub.from_settings(self.user_settings)

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
                category=node.category_display,
                title=node.title,
                user=removed.fullname
            )

            if not auth or auth.user != removed:
                url = node.web_url_for('node_setting')
                message += (
                    u' You can re-authenticate on the <a href="{url}">Settings</a> page.'
                ).format(url=url)
            #
            return message

    def after_set_privacy(self, node, permissions):
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

    def before_fork(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message

        """
        if self.user_settings and self.user_settings.owner == user:
            return (
                'Because you have authenticated the GitHub add-on for this '
                '{cat}, forking it will also transfer your authorization to '
                'the forked {cat}.'
            ).format(
                cat=node.project_or_component,
            )
        return (
            'Because this GitHub add-on has been authenticated by a different '
            'user, forking it will not transfer authentication to the forked '
            '{cat}.'
        ).format(
            cat=node.project_or_component,
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

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), log=True, save=True)

    #########
    # Hooks #
    #########

    # TODO: Should Events be added here?
    # TODO: Move hook logic to service
    def add_hook(self, save=True):

        if self.user_settings:
            connect = GitHub.from_settings(self.user_settings)
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
            connection = GitHub.from_settings(self.user_settings)
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
