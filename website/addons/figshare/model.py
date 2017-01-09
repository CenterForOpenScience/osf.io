# -*- coding: utf-8 -*-

import markupsafe
from modularodm import fields

from framework.auth.decorators import Auth
from framework.exceptions import HTTPError

from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase
from website.oauth.models import ExternalProvider

from website.addons.figshare import messages
from website.addons.figshare.client import FigshareClient
from website.addons.figshare import settings
from website.addons.figshare.serializer import FigshareSerializer

class Figshare(ExternalProvider):
    name = 'figshare'
    short_name = 'figshare'

    client_id = settings.CLIENT_ID
    client_secret = settings.CLIENT_SECRET

    auth_url_base = settings.FIGSHARE_OAUTH_AUTH_ENDPOINT
    callback_url = settings.FIGSHARE_OAUTH_TOKEN_ENDPOINT
    auto_refresh_url = callback_url
    # refresh_time = settings.REFRESH_TIME  # TODO: maybe
    # expiry_time = settings.EXPIRY_TIME
    default_scopes = ['all']

    def handle_callback(self, response):
        """View called when the Oauth flow is completed. Adds a new BoxUserSettings
        record to the user and saves the user's access token and account info.
        """
        client = FigshareClient(response['access_token'])
        about = client.userinfo()

        return {
            'provider_id': about['id'],
            'display_name': '{} {}'.format(about['first_name'], about.get('last_name')),
        }


class FigshareUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = Figshare
    serializer = FigshareSerializer


class FigshareNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = Figshare
    serializer = FigshareSerializer

    folder_id = fields.StringField()
    folder_name = fields.StringField()
    folder_path = fields.StringField()  # hijacked; figshare_type

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Figshare(self.external_account)
        return self._api

    def fetch_folder_name(self):
        return u'{0}:{1}'.format(self.folder_name or 'Unnamed {0}'.format(self.folder_path or ''), self.folder_id)

    def fetch_full_folder_path(self):
        return self.folder_name

    def get_folders(self, **kwargs):
        return FigshareClient(self.external_account.oauth_key).get_folders()

    def archive_errors(self):
        items = []
        if self.folder_path in ('article', 'fileset'):
            article = FigshareClient(self.external_account.oauth_key).article(self.folder_id)
            items = [article]
        else:
            project = FigshareClient(self.external_account.oauth_key).project(self.folder_id)
            items = project['articles'] if project else []
        private = any(
            [item for item in items if item['status'].lower() != 'public']
        )

        if private:
            return 'The figshare {folder_path} <strong>{folder_name}</strong> contains private content that we cannot copy to the registration. If this content is made public on figshare we should then be able to copy those files. You can view those files <a href="{url}" target="_blank">here.</a>'.format(
                folder_path=markupsafe.escape(self.folder_path),
                folder_name=markupsafe.escape(self.folder_name),
                url=self.owner.web_url_for('collect_file_trees'))

    def clear_settings(self):
        self.folder_id = None
        self.folder_name = None
        self.folder_path = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()

        if add_log:
            self.nodelogger.log(action='node_deauthorized', save=True)

        self.clear_auth()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        try:
            # Figshare(self.external_account).refresh_oauth_key()  # TODO: Maybe
            return {'token': self.external_account.oauth_key}
        except Exception as error:  # TODO: specific exception
            raise HTTPError(error.status_code, data={'message_long': error.message})

    def serialize_waterbutler_settings(self):
        if not self.folder_path or not self.folder_id:
            raise exceptions.AddonError('Folder is not configured')
        return {
            'container_type': self.folder_path,
            'container_id': str(self.folder_id),
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='figshare')
        self.owner.add_log(
            'figshare_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['materialized'],
                'filename': metadata['materialized'].strip('/'),
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def set_folder(self, folder_id, auth):
        try:
            info = FigshareClient(self.external_account.oauth_key).get_linked_folder_info(folder_id)
        except HTTPError as e:
            raise exceptions.InvalidFolderError(e.message)

        self.folder_id = info['id']
        self.folder_name = info['name']
        self.folder_path = info['path']
        self.save()

        self.nodelogger.log(action='folder_selected', save=True)

    #############
    # Callbacks #
    #############

    def after_delete(self, node=None, user=None):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()

    def before_page_load(self, node, user):
        """
        :param Node node:
        :param User user:
        :return str: Alert message
        """
        if not self.folder_id:
            return []
        figshare = node.get_addon('figshare')
        # Quit if no user authorization

        node_permissions = 'public' if node.is_public else 'private'

        if figshare.folder_path == 'project':
            if node_permissions == 'private':
                message = messages.BEFORE_PAGE_LOAD_PRIVATE_NODE_MIXED_FS.format(category=node.project_or_component, project_id=figshare.folder_id)
                return [message]
            else:
                message = messages.BEFORE_PAGE_LOAD_PUBLIC_NODE_MIXED_FS.format(category=node.project_or_component, project_id=figshare.folder_id)

        connect = FigshareClient(self.external_account.oauth_key)
        project_is_public = connect.container_is_public(self.folder_id, self.folder_path)

        article_permissions = 'public' if project_is_public else 'private'

        if article_permissions != node_permissions:
            message = messages.BEFORE_PAGE_LOAD_PERM_MISMATCH.format(
                category=node.project_or_component,
                node_perm=node_permissions,
                figshare_perm=article_permissions,
                figshare_id=self.folder_id,
                folder_type=self.folder_path,
            )
            if article_permissions == 'private' and node_permissions == 'public':
                message += messages.BEFORE_PAGE_LOAD_PUBLIC_NODE_PRIVATE_FS.format(folder_type=self.folder_path)
            # No HTML snippets, so escape message all at once
            return [markupsafe.escape(message)]
