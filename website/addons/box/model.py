# -*- coding: utf-8 -*-
import os
import logging
import hashlib
from datetime import datetime

from modularodm import fields, Q
from modularodm.exceptions import ModularOdmException

from framework.auth import Auth
from website.addons.base import exceptions
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, GuidFile

from website.addons.box.utils import BoxNodeLogger
from website.addons.box import settings
from website.addons.box.client import get_client_from_user_settings

from box import CredentialsV2

logger = logging.getLogger(__name__)


class BoxFile(GuidFile):
    """A Box file model with a GUID. Created lazily upon viewing a
    file's detail page.
    """

    #: Full path to the file, e.g. 'My Pictures/foo.png'
    path = fields.StringField(required=True, index=True)

    @property
    def waterbutler_path(self):
        if not self.path.startswith('/'):
            return '/{}'.format(self.path)
        return self.path

    @property
    def provider(self):
        return 'box'

    @property
    def version_identifier(self):
        return 'revision'

    @property
    def unique_identifier(self):
        return hashlib.md5(self.waterbutler_path).hexdigest()

    @classmethod
    def get_or_create(cls, node, path):
        """Get or create a new file record. Return a tuple of the form (obj, created)
        """
        try:
            new = cls.find_one(
                Q('node', 'eq', node) &
                Q('path', 'eq', path)
            )
            created = False
        except ModularOdmException:
            # Create new
            new = cls(node=node, path=path)
            new.save()
            created = True
        return new, created


class BoxUserSettings(AddonUserSettingsBase):
    """Stores user-specific box information, including the Oauth access
    token.
    """

    box_id = fields.StringField(required=False)
    access_token = fields.StringField(required=False)
    refresh_token = fields.StringField(required=False)
    box_info = fields.DictionaryField(required=False)
    token_type = fields.StringField(required=False)
    restricted_to = fields.DictionaryField(required=False)
    last_refreshed = fields.DateTimeField(editable=True)

    # TODO(sloria): The `user` param in unnecessary for AddonUserSettings
    def to_json(self, user=None):
        """Return a dictionary representation of the user settings.
        The dictionary keys and values will be available as variables in
        box_user_settings.mako.
        """
        output = super(BoxUserSettings, self).to_json(self.owner)
        output['has_auth'] = self.has_auth
        return output

    def token_refreshed_callback(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.last_refreshed = datetime.utcnow()
        self.save()

    @property
    def has_auth(self):
        return bool(self.access_token and self.refresh_creds_if_necessary())

    def delete(self, save=True):
        self.clear()
        super(BoxUserSettings, self).delete(save)

    def clear(self):
        """Clear settings and deauthorize any associated nodes."""
        self.box_id = None
        self.access_token = None
        for node_settings in self.boxnodesettings__authorized:
            node_settings.deauthorize(Auth(self.owner))
            node_settings.save()
        return self

    def get_credentialsv2(self):
        return CredentialsV2(
            self.access_token,
            self.refresh_token,
            settings.BOX_KEY,
            settings.BOX_SECRET,
            self.token_refreshed_callback,
        )

    def refresh_creds_if_necessary(self):
        """Checks to see if the access token has expired, or will
        expire within 6 minutes. Returns the status of a refresh
        attempt or True if not required.
        """
        diff = (datetime.utcnow() - self.last_refreshed).total_seconds() / 3600
        if diff > 0.9:
            return self.get_credentialsv2().refresh()
        else:
            return True

    def __repr__(self):
        return u'<BoxUserSettings(user={self.owner.username!r})>'.format(self=self)


class BoxNodeSettings(AddonNodeSettingsBase):

    user_settings = fields.ForeignField(
        'boxusersettings', backref='authorized'
    )

    folder_id = fields.IntegerField(default=None)

    @property
    def folder(self):
        if not self.folder_id:
            return None
        cl = get_client_from_user_settings(self.user_settings)
        return cl.get_folder(self.folder_id)['name']

    @property
    def display_name(self):
        return '{0}: {1}'.format(self.config.full_name, self.folder_id)

    @property
    def has_auth(self):
        """Whether an access token is associated with this node."""
        return bool(self.user_settings and self.user_settings.has_auth)

    def set_folder(self, folder_id, auth):
        self.folder_id = folder_id
        self.save()
        # Add log to node
        nodelogger = BoxNodeLogger(node=self.owner, auth=auth)
        nodelogger.log(action="folder_selected", save=True)

    def set_user_auth(self, user_settings):
        """Import a user's Box authentication and create a NodeLog.

        :param BoxUserSettings user_settings: The user settings to link.
        """
        self.user_settings = user_settings
        nodelogger = BoxNodeLogger(node=self.owner, auth=Auth(user_settings.owner))
        nodelogger.log(action="node_authorized", save=True)

    def find_or_create_file_guid(self, path):
        return BoxFile.get_or_create(self.owner, path)

    # TODO: Is this used? If not, remove this and perhaps remove the 'deleted' field
    def delete(self, save=True):
        self.deauthorize(add_log=False)
        super(BoxNodeSettings, self).delete(save)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        node = self.owner

        if add_log:
            extra = {'folder_id': self.folder_id}
            nodelogger = BoxNodeLogger(node=node, auth=auth)
            nodelogger.log(action="node_deauthorized", extra=extra, save=True)

        self.folder_id = None
        self.user_settings = None

        self.save()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.user_settings.access_token}

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder_id': self.folder_id}

    def create_waterbutler_log(self, auth, action, metadata):
        path = metadata['path']
        self.owner.add_log(
            'box_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': os.path.join(self.folder_id, path),
                'folder': self.folder_id,
                'urls': {
                    'view': self.owner.web_url_for('addon_view_or_download_file', provider='box', action='view', path=path),
                    'download': self.owner.web_url_for('addon_view_or_download_file', provider='box', action='download', path=path),
                },
            },
        )

    ##### Callback overrides #####

    def before_register_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        registration.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.has_auth:
            return (
                u'The contents of Box add-ons cannot be registered at this time; '
                u'the Box folder linked to this {category} will not be included '
                u'as part of this registration.'
            ).format(**locals())

    # backwards compatibility
    before_register = before_register_message

    def before_fork_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        fork.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.owner == user:
            return (u'Because you have authorized the Box add-on for this '
                '{category}, forking it will also transfer your authentication token to '
                'the forked {category}.').format(category=category)

        else:
            return (u'Because the Box add-on has been authorized by a different '
                    'user, forking it will not transfer authentication token to the forked '
                    '{category}.').format(category=category)

    # backwards compatibility
    before_fork = before_fork_message

    def before_remove_contributor_message(self, node, removed):
        """Return warning text to display if removed contributor is the user
        who authorized the Box addon
        """
        if self.user_settings and self.user_settings.owner == removed:
            category = node.project_or_component
            name = removed.fullname
            return (u'The Box add-on for this {category} is authenticated by {name}. '
                    'Removing this user will also remove write access to Box '
                    'unless another contributor re-authenticates the add-on.'
                    ).format(**locals())

    # backwards compatibility
    before_remove_contributor = before_remove_contributor_message

    def after_fork(self, node, fork, user, save=True):
        """After forking, copy user settings if the user is the one who authorized
        the addon.

        :return: A tuple of the form (cloned_settings, message)
        """
        clone, _ = super(BoxNodeSettings, self).after_fork(
            node=node, fork=fork, user=user, save=False
        )

        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = (
                'Box authorization copied to forked {cat}.'
            ).format(
                cat=fork.project_or_component
            )
        else:
            message = (
                u'Box authorization not copied to forked {cat}. You may '
                'authorize this fork on the <a href="{url}">Settings</a> '
                'page.'
            ).format(
                url=fork.web_url_for('node_setting'),
                cat=fork.project_or_component
            )
        if save:
            clone.save()
        return clone, message

    def after_remove_contributor(self, node, removed):
        """If the removed contributor was the user who authorized the Box
        addon, remove the auth credentials from this node.
        Return the message text that will be displayed to the user.
        """
        if self.user_settings and self.user_settings.owner == removed:
            self.user_settings = None
            self.save()
            name = removed.fullname
            url = node.web_url_for('node_setting')
            return (u'Because the Box add-on for this project was authenticated'
                    'by {name}, authentication information has been deleted. You '
                    'can re-authenticate on the <a href="{url}">Settings</a> page'
                    ).format(**locals())

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()
