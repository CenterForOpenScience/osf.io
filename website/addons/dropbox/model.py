# -*- coding: utf-8 -*-
import httplib as http
import logging
import os

from dropbox.client import DropboxOAuth2Flow, DropboxClient
from dropbox.rest import ErrorResponse
from flask import request
import markupsafe

from modularodm import fields

from framework.auth import Auth
from framework.exceptions import HTTPError
from framework.sessions import session

from website.util import web_url_for
from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase
from website.oauth.models import ExternalProvider

from website.addons.dropbox import settings
from website.addons.dropbox.serializer import DropboxSerializer

logger = logging.getLogger(__name__)


class DropboxProvider(ExternalProvider):

    name = 'DropBox'
    short_name = 'dropbox'

    client_id = settings.DROPBOX_KEY
    client_secret = settings.DROPBOX_SECRET

    # Explicitly override auth_url_base as None -- DropboxOAuth2Flow handles this for us
    auth_url_base = None
    callback_url = None
    handle_callback = None

    @property
    def oauth_flow(self):
        if 'oauth_states' not in session.data:
            session.data['oauth_states'] = {}
        if self.short_name not in session.data['oauth_states']:
            session.data['oauth_states'][self.short_name] = {
                'state': None
            }
        return DropboxOAuth2Flow(
            self.client_id,
            self.client_secret,
            redirect_uri=web_url_for(
                'oauth_callback',
                service_name=self.short_name,
                _absolute=True
            ),
            session=session.data['oauth_states'][self.short_name], csrf_token_session_key='state'
        )

    @property
    def auth_url(self):
        return self.oauth_flow.start('force_reapprove=true')

    # Overrides ExternalProvider
    def auth_callback(self, user):
        # TODO: consider not using client library during auth flow
        try:
            access_token, dropbox_user_id, url_state = self.oauth_flow.finish(request.values)
        except (DropboxOAuth2Flow.NotApprovedException, DropboxOAuth2Flow.BadStateException):
            # 1) user cancelled and client library raised exc., or
            # 2) the state was manipulated, possibly due to time.
            # Either way, return and display info about how to properly connect.
            return
        except (DropboxOAuth2Flow.ProviderException, DropboxOAuth2Flow.CsrfException):
            raise HTTPError(http.FORBIDDEN)
        except DropboxOAuth2Flow.BadRequestException:
            raise HTTPError(http.BAD_REQUEST)

        self.client = DropboxClient(access_token)

        info = self.client.account_info()
        return self._set_external_account(
            user,
            {
                'key': access_token,
                'provider_id': info['uid'],
                'display_name': info['display_name'],
            }
        )


class DropboxUserSettings(AddonOAuthUserSettingsBase):
    """Stores user-specific dropbox information.
    token.
    """

    oauth_provider = DropboxProvider
    serializer = DropboxSerializer

    def revoke_remote_oauth_access(self, external_account):
        """Overrides default behavior during external_account deactivation.

        Tells DropBox to remove the grant for the OSF associated with this account.
        """
        client = DropboxClient(external_account.oauth_key)
        try:
            client.disable_access_token()
        except ErrorResponse:
            pass

class DropboxNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):

    oauth_provider = DropboxProvider
    serializer = DropboxSerializer

    folder = fields.StringField(default=None)

    #: Information saved at the time of registration
    #: Note: This is unused right now
    registration_data = fields.DictionaryField()

    _folder_data = None

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = DropboxProvider(self.external_account)
        return self._api

    @property
    def folder_id(self):
        return self.folder

    @property
    def folder_name(self):
        return os.path.split(self.folder or '')[1]

    @property
    def folder_path(self):
        return self.folder

    @property
    def display_name(self):
        return '{0}: {1}'.format(self.config.full_name, self.folder)

    def clear_settings(self):
        self.folder = None

    def fetch_folder_name(self):
        return self.folder

    def set_folder(self, folder, auth):
        self.folder = folder
        # Add log to node
        self.nodelogger.log(action='folder_selected', save=True)

    # TODO: Is this used? If not, remove this and perhaps remove the 'deleted' field
    def delete(self, save=True):
        self.deauthorize(add_log=False)
        super(DropboxNodeSettings, self).delete(save)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        folder = self.folder
        self.clear_settings()

        if add_log:
            extra = {'folder': folder}
            self.nodelogger.log(action='node_deauthorized', extra=extra, save=True)

        self.clear_auth()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.external_account.oauth_key}

    def serialize_waterbutler_settings(self):
        if not self.folder:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder}

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'].strip('/'), provider='dropbox')
        self.owner.add_log(
            'dropbox_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['path'],
                'folder': self.folder,
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def __repr__(self):
        return u'<DropboxNodeSettings(node_id={self.owner._primary_key!r})>'.format(self=self)

    ##### Callback overrides #####

    def before_register_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        registration.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.has_auth:
            return (
                u'The contents of Dropbox add-ons cannot be registered at this time; '
                u'the Dropbox folder linked to this {category} will not be included '
                u'as part of this registration.'
            ).format(category=markupsafe.escape(category))

    # backwards compatibility
    before_register = before_register_message

    def before_remove_contributor_message(self, node, removed):
        """Return warning text to display if removed contributor is the user
        who authorized the Dropbox addon
        """
        if self.user_settings and self.user_settings.owner == removed:
            category = node.project_or_component
            name = removed.fullname
            return (u'The Dropbox add-on for this {category} is authenticated by {name}. '
                    u'Removing this user will also remove write access to Dropbox '
                    u'unless another contributor re-authenticates the add-on.'
                    ).format(category=markupsafe.escape(category),
                             name=markupsafe.escape(name))

    # backwards compatibility
    before_remove_contributor = before_remove_contributor_message

    # Note: Registering Dropbox content is disabled for now; leaving this code
    # here in case we enable registrations later on.
    # @jmcarp
    # def after_register(self, node, registration, user, save=True):
    #     """After registering a node, copy the user settings and save the
    #     chosen folder.
    #
    #     :return: A tuple of the form (cloned_settings, message)
    #     """
    #     clone, message = super(DropboxNodeSettings, self).after_register(
    #         node, registration, user, save=False
    #     )
    #     # Copy user_settings and add registration data
    #     if self.has_auth and self.folder is not None:
    #         clone.user_settings = self.user_settings
    #         clone.registration_data['folder'] = self.folder
    #     if save:
    #         clone.save()
    #     return clone, message

    def after_fork(self, node, fork, user, save=True):
        """After forking, copy user settings if the user is the one who authorized
        the addon.

        :return: A tuple of the form (cloned_settings, message)
        """
        clone, _ = super(DropboxNodeSettings, self).after_fork(
            node=node, fork=fork, user=user, save=False
        )

        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = (
                'Dropbox authorization copied to forked {cat}.'
            ).format(
                cat=markupsafe.escape(fork.project_or_component)
            )
        else:
            message = (
                u'Dropbox authorization not copied to forked {cat}. You may '
                u'authorize this fork on the <u><a href="{url}">Settings</a></u> '
                u'page.'
            ).format(
                url=fork.web_url_for('node_setting'),
                cat=markupsafe.escape(fork.project_or_component)
            )
        if save:
            clone.save()
        return clone, message

    def after_remove_contributor(self, node, removed, auth=None):
        """If the removed contributor was the user who authorized the Dropbox
        addon, remove the auth credentials from this node.
        Return the message text that will be displayed to the user.
        """
        if self.user_settings and self.user_settings.owner == removed:
            self.user_settings = None
            self.save()

            message = (
                u'Because the Dropbox add-on for {category} "{title}" was authenticated '
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

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()
