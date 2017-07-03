# -*- coding: utf-8 -*-

import os
import urlparse

import markupsafe
from modularodm import fields

from framework.auth import Auth

from website import settings
from website.util import web_url_for
from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.gitlab import utils
from website.addons.gitlab.api import GitLabClient
from website.addons.gitlab.serializer import GitLabSerializer
from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab.exceptions import ApiError, NotFoundError, GitLabError
from website.oauth.models import ExternalProvider


hook_domain = gitlab_settings.HOOK_DOMAIN or settings.DOMAIN


class GitLabProvider(ExternalProvider):
    name = 'GitLab'
    short_name = 'gitlab'

    @property
    def auth_url_base(self):
        return 'https://{0}{1}'.format('gitlab.com', '/oauth/authorize')

    @property
    def callback_url(self):
        return 'https://{0}{1}'.format('gitlab.com', '/oauth/token')

    @property
    def client_secret(self):
        return ''

    @property
    def client_id(self):
        return ''

    def handle_callback(self, response):
        """View called when the OAuth flow is completed. Adds a new GitLabUserSettings
        record to the user and saves the account info.
        """
        client = GitLabClient(
            access_token=response['access_token']
        )

        user_info = client.user()

        return {
            'provider_id': client.host,
            'profile_url': user_info['web_url'],
            'oauth_key': response['access_token'],
            'display_name': client.host
        }


class GitLabUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = GitLabProvider
    serializer = GitLabSerializer


class GitLabNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = GitLabProvider
    serializer = GitLabSerializer

    user = fields.StringField()
    repo = fields.StringField()
    repo_id = fields.StringField()
    hook_id = fields.StringField()
    hook_secret = fields.StringField()

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
    def has_auth(self):
        return bool(self.user_settings and self.user_settings.has_auth)

    @property
    def complete(self):
        return self.has_auth and self.repo is not None and self.user is not None

    def authorize(self, user_settings, save=False):
        self.user_settings = user_settings
        self.owner.add_log(
            action='gitlab_node_authorized',
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
        self.repo_id = None
        self.hook_id = None
        self.hook_secret = None

    def deauthorize(self, auth=None, log=True):
        self.delete_hook(save=False)
        self.clear_settings()
        if log:
            self.owner.add_log(
                action='gitlab_node_deauthorized',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                },
                auth=auth,
            )

        self.clear_auth()

    def delete(self, save=False):
        super(GitLabNodeSettings, self).delete(save=False)
        self.deauthorize(log=False)
        if save:
            self.save()

    @property
    def repo_url(self):
        if self.repo:
            return 'https://{0}/{1}'.format(self.external_account.display_name, self.repo)

    @property
    def short_url(self):
        if self.repo:
            return self.repo

    @property
    def is_private(self):
        connection = GitLabClient(external_account=self.external_account)
        return not connection.repo(repo_id=self.repo_id)['public']

    def to_json(self, user):

        ret = super(GitLabNodeSettings, self).to_json(user)
        user_settings = user.get_addon('gitlab')
        ret.update({
            'user_has_auth': user_settings and user_settings.has_auth,
            'is_registration': self.owner.is_registration,
        })

        if self.user_settings and self.user_settings.has_auth:

            valid_credentials = False
            owner = self.user_settings.owner
            connection = GitLabClient(external_account=self.external_account)

            valid_credentials = True
            try:
                repos = connection.repos()

            except GitLabError:
                valid_credentials = False

            if owner == user:
                ret.update({'repos': repos})

            ret.update({
                'node_has_auth': True,
                'gitlab_user': self.user or '',
                'gitlab_repo': self.repo or '',
                'gitlab_repo_id': self.repo_id if self.repo_id is not None else '0',
                'gitlab_repo_full_name': '{0} / {1}'.format(self.user, self.repo) if (self.user and self.repo) else '',
                'auth_osf_name': owner.fullname,
                'auth_osf_url': owner.url,
                'auth_osf_id': owner._id,
                'gitlab_host': self.external_account.display_name,
                'gitlab_user_name': self.external_account.display_name,
                'gitlab_user_url': self.external_account.profile_url,
                'is_owner': owner == user,
                'valid_credentials': valid_credentials,
                'addons_url': web_url_for('user_addons'),
                'files_url': self.owner.web_url_for('collect_file_trees')
            })
        return ret

    def serialize_waterbutler_credentials(self):
        if not self.complete or not self.repo:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.external_account.provider_id}

    def serialize_waterbutler_settings(self):
        if not self.complete:
            raise exceptions.AddonError('Repo is not configured')
        return {
            'host': 'https://{}'.format(self.external_account.display_name),
            'owner': self.user,
            'repo': self.repo,
            'repo_id': self.repo_id
        }

    def create_waterbutler_log(self, auth, action, metadata):
        path = metadata['path']

        url = self.owner.web_url_for('addon_view_or_download_file', path=path, provider='gitlab')

        if not metadata.get('extra'):
            sha = None
            urls = {}
        else:
            sha = metadata['extra']['fileSha']
            urls = {
                'view': '{0}?ref={1}'.format(url, sha),
                'download': '{0}?action=download&ref={1}'.format(url, sha)
            }

        self.owner.add_log(
            'gitlab_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': path,
                'urls': urls,
                'gitlab': {
                    'host': 'https://{0}'.format(self.external_account.display_name),
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

        connect = GitLabClient(external_account=self.external_account)

        try:
            repo = connect.repo(self.repo_id)
        except (ApiError, GitLabError):
            return

        node_permissions = 'public' if node.is_public else 'private'
        repo_permissions = 'private' if not repo['public'] else 'public'
        if repo_permissions != node_permissions:
            message = (
                'Warning: This OSF {category} is {node_perm}, but the GitLab '
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
                    ' Users can view the contents of this private GitLab '
                    'repository through this public project.'
                )
            else:
                message += (
                    ' The files in this GitLab repo can be viewed on GitLab '
                    '<u><a href="{url}">here</a></u>.'
                ).format(url = repo['http_url_to_repo'])
            messages.append(message)
            return messages

    def before_remove_contributor_message(self, node, removed):
        """

        :param Node node:
        :param User removed:
        :return str: Alert message

        """
        try:
            message = (super(GitLabNodeSettings, self).before_remove_contributor_message(node, removed) +
            'You can download the contents of this repository before removing '
            'this contributor <u><a href="{url}">here</a></u>.'.format(
                url=node.api_url + 'gitlab/tarball/'
            ))
        except TypeError:
            # super call returned None due to lack of user auth
            return None
        else:
            return message

    # backwards compatibility -- TODO: is this necessary?
    before_remove_contributor = before_remove_contributor_message

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
                u'Because the GitLab add-on for {category} "{title}" was authenticated '
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
        :return tuple: Tuple of cloned settings and alert message
        """
        clone, _ = super(GitLabNodeSettings, self).after_fork(
            node, fork, user, save=False
        )

        # Copy authentication if authenticated by forking user
        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = (
                'GitLab authorization copied to forked {cat}.'
            ).format(
                cat=markupsafe.escape(fork.project_or_component),
            )
        else:
            message = (
                'GitLab authorization not copied to forked {cat}. You may '
                'authorize this fork on the <u><a href={url}>Settings</a></u> '
                'page.'
            ).format(
                cat=markupsafe.escape(fork.project_or_component),
                url=fork.url + 'settings/'
            )

        if save:
            clone.save()

        return clone, message

    def before_make_public(self, node):
        try:
            is_private = self.is_private
        except NotFoundError:
            return None
        if is_private:
            return (
                'This {cat} is connected to a private GitLab repository. Users '
                '(other than contributors) will not be able to see the '
                'contents of this repo unless it is made public on GitLab.'
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
            connect = GitLabClient(external_account=self.external_account)
            secret = utils.make_hook_secret()
            hook = connect.add_hook(
                self.user, self.repo,
                'web',
                {
                    'url': urlparse.urljoin(
                        hook_domain,
                        os.path.join(
                            self.owner.api_url, 'gitlab', 'hook/'
                        )
                    ),
                    'content_type': gitlab_settings.HOOK_CONTENT_TYPE,
                    'secret': secret,
                },
                events=gitlab_settings.HOOK_EVENTS,
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
            connection = GitLabClient(external_account=self.external_account)
            try:
                response = connection.delete_hook(self.user, self.repo, self.hook_id)
            except (GitLabError, NotFoundError):
                return False
            if response:
                self.hook_id = None
                if save:
                    self.save()
                return True
        return False
