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

from website.addons.bitbucket.api import BitbucketClient
from website.addons.bitbucket.serializer import BitbucketSerializer
from website.addons.bitbucket import settings as bitbucket_settings
from website.addons.bitbucket.exceptions import NotFoundError
from website.oauth.models import ExternalProvider


hook_domain = bitbucket_settings.HOOK_DOMAIN or settings.DOMAIN


class BitbucketProvider(ExternalProvider):
    """Provider to handler Bitbucket OAuth workflow

    API Docs::

    * https://developer.atlassian.com/bitbucket/api/2/reference/meta/authentication

    * https://confluence.atlassian.com/bitbucket/oauth-on-bitbucket-cloud-238027431.html

    """

    name = 'Bitbucket'
    short_name = 'bitbucket'

    client_id = bitbucket_settings.CLIENT_ID
    client_secret = bitbucket_settings.CLIENT_SECRET

    auth_url_base = bitbucket_settings.OAUTH_AUTHORIZE_URL
    callback_url = bitbucket_settings.OAUTH_ACCESS_TOKEN_URL
    default_scopes = bitbucket_settings.SCOPE

    auto_refresh_url = callback_url
    refresh_time = bitbucket_settings.REFRESH_TIME
    expiry_time = bitbucket_settings.EXPIRY_TIME

    def handle_callback(self, response):
        """View called when the OAuth flow is completed. Adds a new BitbucketUserSettings
        record to the user and saves the account info.
        """

        client = BitbucketClient(access_token=response['access_token'])
        user_info = client.get_user()

        return {
            'provider_id': user_info['uuid'],
            'profile_url': user_info['links']['html']['href'],
            'display_name': user_info['username']
        }

    def fetch_access_token(self, force_refresh=False):
        self.refresh_oauth_key(force=force_refresh)
        return self.account.oauth_key


class BitbucketUserSettings(AddonOAuthUserSettingsBase):
    """Stores user-specific bitbucket information

    Quirks::

    * Bitbucket does not support remote revocation of access tokens.

    """
    oauth_provider = BitbucketProvider
    serializer = BitbucketSerializer

    # Required for importing username from social profile configuration page
    # Assumes oldest connected account is primary.
    @property
    def public_id(self):
        bitbucket_accounts = [
            a for a in self.owner.external_accounts
            if a.provider == self.oauth_provider.short_name
        ]
        if bitbucket_accounts:
            return bitbucket_accounts[0].display_name
        return None


class BitbucketNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = BitbucketProvider
    serializer = BitbucketSerializer

    user = fields.StringField()
    repo = fields.StringField()
    hook_id = fields.StringField()

    _api = None

    @property
    def api(self):
        """Authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = BitbucketProvider(self.external_account)
        return self._api

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
            action='bitbucket_node_authorized',
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

    def deauthorize(self, auth=None, log=True):
        # self.delete_hook(save=False)
        self.clear_settings()
        if log:
            self.owner.add_log(
                action='bitbucket_node_deauthorized',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                },
                auth=auth,
            )

        self.clear_auth()

    def delete(self, save=False):
        super(BitbucketNodeSettings, self).delete(save=False)
        self.deauthorize(log=False)
        if save:
            self.save()

    @property
    def repo_url(self):
        if self.user and self.repo:
            return 'https://bitbucket.org/{0}/{1}/'.format(
                self.user, self.repo
            )

    @property
    def short_url(self):
        if self.user and self.repo:
            return '/'.join([self.user, self.repo])

    @property
    def is_private(self):
        connection = BitbucketClient(access_token=self.external_account.oauth_key)
        return connection.repo(user=self.user, repo=self.repo)['is_private']

    def fetch_access_token(self):
        return self.api.fetch_access_token()

    # TODO: Delete me and replace with serialize_settings / Knockout
    def to_json(self, user):
        ret = super(BitbucketNodeSettings, self).to_json(user)
        user_settings = user.get_addon('bitbucket')
        ret.update({
            'user_has_auth': user_settings and user_settings.has_auth,
            'is_registration': self.owner.is_registration,
        })
        if self.user_settings and self.user_settings.has_auth:
            valid_credentials = False
            owner = self.user_settings.owner
            connection = BitbucketClient(access_token=self.external_account.oauth_key)

            # TODO: Fetch repo list client-side
            # Since /user/repos excludes organization repos to which the
            # current user has push access, we have to make extra requests to
            # find them
            valid_credentials = True
            try:
                mine = connection.repos()
                ours = connection.team_repos()
                repo_names = [
                    '{0} / {1}'.format(repo['owner']['username'], repo['name'])
                    for repo in mine + ours
                ]
            except Exception:
                repo_names = []
                valid_credentials = False

            if owner == user:
                ret.update({'repo_names': repo_names})
            ret.update({
                'node_has_auth': True,
                'bitbucket_user': self.user or '',
                'bitbucket_repo': self.repo or '',
                'bitbucket_repo_full_name': '{0} / {1}'.format(self.user, self.repo) if (self.user and self.repo) else '',
                'auth_osf_name': owner.fullname,
                'auth_osf_url': owner.url,
                'auth_osf_id': owner._id,
                'bitbucket_user_name': self.external_account.display_name,
                'bitbucket_user_url': self.external_account.profile_url,
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

        url = self.owner.web_url_for('addon_view_or_download_file', path=path, provider='bitbucket')

        sha, urls = None, {}
        try:
            sha = metadata['extra']['commitSha']
            urls = {
                'view': '{0}?commitSha={1}'.format(url, sha),
                'download': '{0}?action=download&commitSha={1}'.format(url, sha)
            }
        except KeyError:
            pass

        self.owner.add_log(
            'bitbucket_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': path,
                'urls': urls,
                'bitbucket': {
                    'user': self.user,
                    'repo': self.repo,
                    'commitSha': sha,
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

        node_permissions = 'public' if node.is_public else 'private'
        repo_permissions = 'private' if self.is_private else 'public'
        if repo_permissions != node_permissions:
            message = (
                'Warning: This OSF {category} is {node_perm}, but the Bitbucket '
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
                    ' Users can view the contents of this private Bitbucket '
                    'repository through this public project.'
                )
            else:
                message += (
                    ' The files in this Bitbucket repo can be viewed on Bitbucket '
                    '<u><a href="https://bitbucket.org/{user}/{repo}/">here</a></u>.'
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
            message = (super(BitbucketNodeSettings, self).before_remove_contributor_message(node, removed) +
            'You can download the contents of this repository before removing '
            'this contributor <u><a href="{url}">here</a></u>.'.format(
                url=node.api_url + 'bitbucket/tarball/'
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
                u'Because the Bitbucket add-on for {category} "{title}" was authenticated '
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
        clone, _ = super(BitbucketNodeSettings, self).after_fork(
            node, fork, user, save=False
        )

        # Copy authentication if authenticated by forking user
        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = (
                'Bitbucket authorization copied to forked {cat}.'
            ).format(
                cat=markupsafe.escape(fork.project_or_component),
            )
        else:
            message = (
                'Bitbucket authorization not copied to forked {cat}. You may '
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
                'This {cat} is connected to a private Bitbucket repository. Users '
                '(other than contributors) will not be able to see the '
                'contents of this repo unless it is made public on Bitbucket.'
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
            connect = BitbucketClient(access_token=self.external_account.oauth_key)
            hook = connect.add_hook(
                self.user, self.repo,
                {
                    'description': 'OSF Webhook for project {}'.format(self.owner),
                    'url': urlparse.urljoin(
                        hook_domain,
                        os.path.join(
                            self.owner.api_url, 'bitbucket', 'hook/'
                        )
                    ),
                    'active': True,
                    'events': bitbucket_settings.HOOK_EVENTS,
                }
            )

            if hook:
                self.hook_id = hook.id
                if save:
                    self.save()

    def delete_hook(self, save=True):
        """Delete a webhook for this repository.

        :param bool save: whether or not to save the node settings after hook deletion
        :return bool: Hook was deleted
        """
        if self.user_settings and self.hook_id:
            connection = BitbucketClient(access_token=self.external_account.oauth_key)
            try:
                response = connection.delete_hook(self.user, self.repo, self.hook_id)
            except (Exception, NotFoundError):
                return False
            if response:
                self.hook_id = None
                if save:
                    self.save()
                return True
        return False
