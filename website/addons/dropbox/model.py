# -*- coding: utf-8 -*-
import os
import hashlib
import logging
import urllib

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework import fields
from framework.auth import Auth
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, GuidFile

from website.addons.dropbox.client import get_node_addon_client
from website.addons.dropbox.utils import clean_path, DropboxNodeLogger

logger = logging.getLogger(__name__)
debug = logger.debug


class DropboxFile(GuidFile):
    """A Dropbox file model with a GUID. Created lazily upon viewing a
    file's detail page.
    """

    #: Full path to the file, e.g. 'My Pictures/foo.png'
    path = fields.StringField(required=True, index=True)

    #: Stored metadata from the dropbox API
    #: See https://www.dropbox.com/developers/core/docs#metadata
    metadata = fields.DictionaryField(required=False)

    def url(self, guid=True, rev='', *args, **kwargs):
        """The web url for the file.

        :param bool guid: Whether to return the short URL
        """
        # Short URLS must be built 'manually'
        if guid:
            # If returning short URL, urlencode the kwargs to build querystring
            base_url = os.path.join('/', self._primary_key)
            args = {'rev': rev}
            args.update(**kwargs)
            querystring = urllib.urlencode(args)
            url = '/?'.join([base_url, querystring])
        else:
            url = self.node.web_url_for('dropbox_view_file', path=self.path,
                rev=rev, **kwargs)
        return url

    @property
    def file_url(self):
        if self.path is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('dropbox', 'files', self.path)

    def download_url(self, guid=True, rev='', *args, **kwargs):
        """Return the download url for the file.

        :param bool guid: Whether to return the short URL
        """
        # Short URLS must be built 'manually'
        if guid:
            # If returning short URL, urlencode the kwargs to build querystring
            base_url = os.path.join('/', self._primary_key, 'download/')
            args = {'rev': rev}
            args.update(**kwargs)
            querystring = urllib.urlencode(args)
            url = '?'.join([base_url, querystring])
        else:
            url = self.node.web_url_for('dropbox_download',
                    path=self.path, _absolute=True, rev=rev, **kwargs)
        return url

    def update_metadata(self, client=None, rev=''):
        cl = client or get_node_addon_client(self.node.get_addon('dropbox'))
        self.metadata = cl.metadata(self.path, list=False, rev=rev)

    def get_metadata(self, client=None, force=False, rev=''):
        """Gets the file metadata from the Dropbox API (cached)."""
        if force or (not self.metadata):
            self.update_metadata(client=client, rev=rev)
            self.save()
        return self.metadata

    def get_cache_filename(self, client=None, rev=''):
        if not rev:
            metadata = self.get_metadata(client=client, rev=rev, force=True)
            revision = metadata['rev']
        else:
            revision = rev
        # Note: Use hash of file path instead of file path in case paths are
        # very long; see https://github.com/CenterForOpenScience/openscienceframework.org/issues/769
        return u'{digest}_{rev}.html'.format(
            digest=hashlib.md5(self.path).hexdigest(),
            rev=revision,
        )

    @classmethod
    def get_or_create(cls, node, path):
        """Get or create a new file record. Return a tuple of the form (obj, created)
        """
        cleaned_path = clean_path(path)
        try:
            new = cls.find_one(
                Q('node', 'eq', node) &
                Q('path', 'eq', cleaned_path)
            )
            created = False
        except ModularOdmException:
            # Create new
            new = cls(node=node, path=cleaned_path)
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
    def has_auth(self):
        """Whether an access token is associated with this node."""
        return bool(self.user_settings and self.user_settings.has_auth)

    def set_folder(self, folder, auth):
        self.folder = folder
        # Add log to node
        nodelogger = DropboxNodeLogger(node=self.owner, auth=auth)
        nodelogger.log(action="folder_selected", save=True)

    def set_user_auth(self, user_settings):
        """Import a user's Dropbox authentication and create a NodeLog.

        :param DropboxUserSettings user_settings: The user settings to link.
        """
        node = self.owner
        self.user_settings = user_settings
        nodelogger = DropboxNodeLogger(node=self.owner, auth=Auth(user_settings.owner))
        nodelogger.log(action="node_authorized", save=True)

    def delete(self, save=True):
        self.deauthorize(add_log=False)
        super(DropboxNodeSettings, self).delete(save)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        node = self.owner
        folder = self.folder

        self.folder = None
        self.user_settings = None

        if add_log:
            extra = {'folder': folder}
            nodelogger = DropboxNodeLogger(node=node, auth=auth)
            nodelogger.log(action="node_deauthorized", extra=extra, save=True)

    def __repr__(self):
        return u'<DropboxNodeSettings(node_id={self.owner._primary_key!r})>'.format(self=self)

    ##### Callback overrides #####

    # def before_register_message(self, node, user):
    #     """Return warning text to display if user auth will be copied to a
    #     registration.
    #     """
    #     category, title = node.project_or_component, node.title
    #     if self.user_settings and self.user_settings.has_auth:
    #         return (u'Registering {category} "{title}" will copy Dropbox add-on '
    #                 'authentication to the registered {category}.').format(**locals())
    #
    # # backwards compatibility
    # before_register = before_register_message

    def before_fork_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        fork.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.owner == user:
            return (u'Because you have authorized the Dropbox add-on for this '
                '{category}, forking it will also transfer your authentication to '
                'the forked {category}.').format(category=category)

        else:
            return (u'Because the Dropbox add-on has been authorized by a different '
                    'user, forking it will not transfer authentication to the forked '
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
            message = 'Dropbox authorization copied to fork.'
        else:
            message = (u'Dropbox authorization not copied to fork. You may '
                        'authorize this fork on the <a href="{url}">Settings</a>'
                        'page.').format(
                        url=fork.web_url_for('node_setting'))
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
            return (u'Because the Dropbox add-on for this project was authenticated'
                    'by {name}, authentication information has been deleted. You '
                    'can re-authenticate on the <a href="{url}">Settings</a> page'
                    ).format(**locals())

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()
