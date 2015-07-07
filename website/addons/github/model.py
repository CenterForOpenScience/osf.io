# -*- coding: utf-8 -*-

import os
import urlparse
import itertools
import httplib as http

import pymongo
from github3 import GitHubError
from modularodm import fields

from framework.auth import Auth
from framework.mongo import StoredObject

from website import settings
from website.util import web_url_for
from website.addons.base import GuidFile
from website.addons.base import exceptions
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.github import utils
from website.addons.github.api import GitHub
from website.addons.github import settings as github_settings
from website.addons.github.exceptions import ApiError, NotFoundError, TooBigToRenderError


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


class AddonGitHubOauthSettings(StoredObject):
    """
    this model address the problem if we have two osf user link
    to the same github user and their access token conflicts issue
    """

    #github user id, for example, "4974056"
    # Note that this is a numeric ID, not the user's login.
    github_user_id = fields.StringField(primary=True, required=True)

    #github user name this is the user's login
    github_user_name = fields.StringField()
    oauth_access_token = fields.StringField()
    oauth_token_type = fields.StringField()


class AddonGitHubUserSettings(AddonUserSettingsBase):

    oauth_state = fields.StringField()
    oauth_settings = fields.ForeignField(
        'addongithuboauthsettings', backref='accessed'
    )

    @property
    def has_auth(self):
        if self.oauth_settings:
            return self.oauth_settings.oauth_access_token is not None
        return False

    @property
    def github_user_name(self):
        if self.oauth_settings:
            return self.oauth_settings.github_user_name
        return None

    @github_user_name.setter
    def github_user_name(self, user_name):
        self.oauth_settings.github_user_name = user_name

    @property
    def oauth_access_token(self):
        if self.oauth_settings:
            return self.oauth_settings.oauth_access_token
        return None

    @oauth_access_token.setter
    def oauth_access_token(self, oauth_access_token):
        self.oauth_settings.oauth_access_token = oauth_access_token

    @property
    def oauth_token_type(self):
        if self.oauth_settings:
            return self.oauth_settings.oauth_token_type
        return None

    @oauth_token_type.setter
    def oauth_token_type(self, oauth_token_type):
        self.oauth_settings.oauth_token_type = oauth_token_type

    # Required for importing username from social profile configuration page
    @property
    def public_id(self):
        if self.oauth_settings:
            return self.oauth_settings.github_user_name
        return None

    def save(self, *args, **kwargs):
        if self.oauth_settings:
            self.oauth_settings.save()
        return super(AddonGitHubUserSettings, self).save(*args, **kwargs)

    def to_json(self, user):
        ret = super(AddonGitHubUserSettings, self).to_json(user)
        ret.update({
            'authorized': self.has_auth,
            'authorized_github_user': self.github_user_name if self.github_user_name else '',
            'show_submit': False,
        })
        return ret

    def revoke_token(self):
        connection = GitHub.from_settings(self)
        try:
            connection.revoke_token()
        except GitHubError as error:
            if error.code == http.UNAUTHORIZED:
                return (
                    'Your GitHub credentials were removed from the OSF, but we '
                    'were unable to revoke your access token from GitHub. Your '
                    'GitHub credentials may no longer be valid.'
                )
            raise

    def clear_auth(self, auth=None, save=False):
        for node_settings in self.addongithubnodesettings__authorized:
            node_settings.deauthorize(auth=auth, save=True)

        # if there is only one osf user linked to this github user oauth, revoke the token,
        # otherwise, disconnect the osf user from the addongithuboauthsettings
        if self.oauth_settings:
            if len(self.oauth_settings.addongithubusersettings__accessed) <= 1:
                self.revoke_token()

        # Clear tokens on oauth_settings
            self.oauth_settings = None
        if save:
            self.save()

    def delete(self, save=False):
        self.clear_auth(save=False)
        super(AddonGitHubUserSettings, self).delete(save=save)


class AddonGitHubNodeSettings(StorageAddonBase, AddonNodeSettingsBase):

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

    def find_or_create_file_guid(self, path):
        return GithubGuidFile.get_or_create(node=self.owner, path=path)

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
        super(AddonGitHubNodeSettings, self).delete(save=False)
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
        connection = GitHub.from_settings(self.user_settings)
        return connection.repo(user=self.user, repo=self.repo).private

    # TODO: Delete me and replace with serialize_settings / Knockout
    def to_json(self, user):
        ret = super(AddonGitHubNodeSettings, self).to_json(user)
        user_settings = user.get_addon('github')
        ret.update({
            'user_has_auth': user_settings and user_settings.has_auth,
            'is_registration': self.owner.is_registration,
        })
        if self.user_settings and self.user_settings.has_auth:
            valid_credentials = False
            owner = self.user_settings.owner
            if user_settings and user_settings.owner == owner:
                connection = GitHub.from_settings(user_settings)
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
                except GitHubError as error:
                    if error.code == http.UNAUTHORIZED:
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
