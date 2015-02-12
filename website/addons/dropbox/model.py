# -*- coding: utf-8 -*-
import os
import logging

from modularodm import fields, Q
from modularodm.exceptions import ModularOdmException

from framework.auth import Auth
from website.addons.base import exceptions
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, GuidFile

from website.addons.dropbox.utils import clean_path, DropboxNodeLogger
from website.addons.dropbox.client import get_node_addon_client

logger = logging.getLogger(__name__)


class DropboxFile(GuidFile):
    """A Dropbox file model with a GUID. Created lazily upon viewing a
    file's detail page.
    """

    #: Full path to the file, e.g. 'My Pictures/foo.png'
    path = fields.StringField(required=True, index=True)

    @property
    def waterbutler_path(self):
        path = '/' + self.path
        if self.folder == '/':
            return path
        return path.replace(self.folder, '', 1)

    @property
    def folder(self):
        return self.node.get_addon('dropbox').folder

    @property
    def provider(self):
        return 'dropbox'

    @property
    def version_identifier(self):
        return 'revision'

    @property
    def unique_identifier(self):
        return self._metadata_cache['extra']['revisionId']

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


class DropboxUserSettings(AddonUserSettingsBase):
    """Stores user-specific dropbox information, including the Oauth access
    token.
    """

    dropbox_id = fields.StringField(required=False)
    access_token = fields.StringField(required=False)
    dropbox_info = fields.DictionaryField(required=False)

    # TODO(sloria): The `user` param in unnecessary for AddonUserSettings
    def to_json(self, user=None):
        """Return a dictionary representation of the user settings.
        The dictionary keys and values will be available as variables in
        dropbox_user_settings.mako.
        """
        output = super(DropboxUserSettings, self).to_json(self.owner)
        output['has_auth'] = self.has_auth
        return output

    @property
    def has_auth(self):
        return bool(self.access_token)

    def delete(self, save=True):
        self.clear()
        super(DropboxUserSettings, self).delete(save)

    def clear(self):
        """Clear settings and deauthorize any associated nodes."""
        self.dropbox_id = None
        self.access_token = None
        for node_settings in self.dropboxnodesettings__authorized:
            node_settings.deauthorize(Auth(self.owner))
            node_settings.save()
        return self

    def __repr__(self):
        return u'<DropboxUserSettings(user={self.owner.username!r})>'.format(self=self)


class DropboxNodeSettings(AddonNodeSettingsBase):

    user_settings = fields.ForeignField(
        'dropboxusersettings', backref='authorized'
    )

    folder = fields.StringField(default=None)

    #: Information saved at the time of registration
    #: Note: This is unused right now
    registration_data = fields.DictionaryField()

    @property
    def display_name(self):
        return '{0}: {1}'.format(self.config.full_name, self.folder)

    @property
    def has_auth(self):
        """Whether an access token is associated with this node."""
        return bool(self.user_settings and self.user_settings.has_auth)

    def find_or_create_file_guid(self, path):
        return DropboxFile.get_or_create(self.owner, clean_path(os.path.join(self.folder, path.lstrip('/'))))

    def set_folder(self, folder, auth):
        if self.folder != folder:
            # configure comments
            self.hide_all_comments()
            client = get_node_addon_client(self)

        self.folder = folder
        self.show_comments(client, folder)
        # Add log to node
        nodelogger = DropboxNodeLogger(node=self.owner, auth=auth)
        nodelogger.log(action="folder_selected", save=True)

    def set_user_auth(self, user_settings):
        """Import a user's Dropbox authentication and create a NodeLog.

        :param DropboxUserSettings user_settings: The user settings to link.
        """
        self.user_settings = user_settings
        nodelogger = DropboxNodeLogger(node=self.owner, auth=Auth(user_settings.owner))
        nodelogger.log(action="node_authorized", save=True)

    # TODO: Is this used? If not, remove this and perhaps remove the 'deleted' field
    def delete(self, save=True):
        self.deauthorize(add_log=False)
        super(DropboxNodeSettings, self).delete(save)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        node = self.owner
        folder = self.folder

        self.folder = None
        self.user_settings = None

        self.hide_all_comments()

        if add_log:
            extra = {'folder': folder}
            nodelogger = DropboxNodeLogger(node=node, auth=auth)
            nodelogger.log(action="node_deauthorized", extra=extra, save=True)

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.user_settings.access_token}

    def serialize_waterbutler_settings(self):
        if not self.folder:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder}

    def create_waterbutler_log(self, auth, action, metadata):
        cleaned_path = clean_path(os.path.join(self.folder, metadata['path']))
        url = self.owner.web_url_for('addon_view_or_download_file', path=cleaned_path, provider='dropbox')

        self.owner.add_log(
            'dropbox_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': cleaned_path,
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
            ).format(**locals())

    # backwards compatibility
    before_register = before_register_message

    def before_fork_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        fork.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.owner == user:
            return (u'Because you have authorized the Dropbox add-on for this '
                '{category}, forking it will also transfer your authentication token to '
                'the forked {category}.').format(category=category)

        else:
            return (u'Because the Dropbox add-on has been authorized by a different '
                    'user, forking it will not transfer authentication token to the forked '
                    '{category}.').format(category=category)

    # backwards compatibility
    before_fork = before_fork_message

    def before_remove_contributor_message(self, node, removed):
        """Return warning text to display if removed contributor is the user
        who authorized the Dropbox addon
        """
        if self.user_settings and self.user_settings.owner == removed:
            category = node.project_or_component
            name = removed.fullname
            return (u'The Dropbox add-on for this {category} is authenticated by {name}. '
                    'Removing this user will also remove write access to Dropbox '
                    'unless another contributor re-authenticates the add-on.'
                    ).format(**locals())

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
                cat=fork.project_or_component
            )
        else:
            message = (
                u'Dropbox authorization not copied to forked {cat}. You may '
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
        """If the removed contributor was the user who authorized the Dropbox
        addon, remove the auth credentials from this node.
        Return the message text that will be displayed to the user.
        """
        if self.user_settings and self.user_settings.owner == removed:
            self.user_settings = None
            self.save()
            name = removed.fullname
            url = node.web_url_for('node_setting')
            self.hide_all_comments()
            return (u'Because the Dropbox add-on for this project was authenticated'
                    'by {name}, authentication information has been deleted. You '
                    'can re-authenticate on the <a href="{url}">Settings</a> page'
                    ).format(**locals())

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def hide_all_comments(self):
        files_id = DropboxFile.find(Q('node', 'eq', self.owner))
        for file_id in files_id:
            db_file = DropboxFile.load(file_id)
            for comment in getattr(db_file, 'comment_target', []):
                comment.hide(save=True)

    def show_comments(self, client, path):
        dropbox_files = self.get_existing_files(client)
        for dropbox_file in dropbox_files:
            for comment in getattr(dropbox_file, 'comment_target', []):
                comment.show(save=True)

    def get_existing_files(self, connection=None):
        if not self.folder:
            return list()
        if not connection:
            connection = get_node_addon_client(self)
        metadata = connection.metadata(self.folder)
        dropbox_files = []
        queue = list(metadata['contents'])
        while len(queue) > 0:
            content = queue.pop(0)
            if content['is_dir']:
                queue.extend(connection.metadata(content['path'])['contents'])
            else:
                path = content['path']
                path = clean_path(path)
                try:
                    guid = DropboxFile.find_one(
                        Q('node', 'eq', self.owner) &
                        Q('path', 'eq', path)
                    )
                except:
                    continue
                dropbox_files.append(guid)
        return dropbox_files