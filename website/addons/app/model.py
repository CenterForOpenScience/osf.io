# -*- coding: utf-8 -*-
"""Persistence layer for the app addon.
"""
import os

from modularodm import fields

from framework import Guid, GuidStoredObject

from website.addons.base import AddonNodeSettingsBase


class AppNodeSettings(GuidStoredObject, AddonNodeSettingsBase):

    redirect_mode = 'proxy'
    # _id = fields.StringField(primary=True)

    custom_routes = fields.DictionaryField()
    allow_queries = fields.BooleanField(default=False)
    allow_public_read = fields.BooleanField(default=True)

    def _guid_to_metadata(self, guid):
        """Resolve a Guid to a metadata object
        :param guid (str, Guid) The guid to attach data to
        :return Metadata
        """
        if isinstance(guid, Guid):
            return guid[self.namespace]
        else:
            return Guid.load(guid)[self.namespace]

    @property
    def deep_url(self):
        return os.path.join(self.owner.deep_url, 'application')

    @property
    def name(self):
        # Todo possibly store this for easier querying
        return self.owner.title

    @property
    def namespace(self):
        return self._id

    def get_data(self, guid):
        return self._guid_to_metadata(guid)

    def attach_data(self, guid, data):
        """Attach a dictionary to the specified guid under this applications
        namespace.
        :param guid (str, Guid) The guid to attach data to
        :param data dict The metadata to store
        """
        metastore = self._guid_to_metadata(guid)

        metastore.update(data)
        metastore.save()

    def delete_data(self, guid, key=None):
        metadata = self._guid_to_metadata(guid)
        if key:
            del metadata[key]
            metadata.save()
        else:
            metadata.remove()

    def add_custom_route(self, route, map_to):
        self.custom_routes[route] = map_to
        self.save()

    def resolve_url(self, url):
        return self.custom_routes[url]

    ##### Callback overrides #####

    def before_register_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        registration.
        """
        return 'This application addon can not be registered.'

    # backwards compatibility
    before_register = before_register_message

    def before_fork_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        fork.
        """
        return "The application addon can not be forked."

    # backwards compatibility
    before_fork = before_fork_message

    def before_remove_contributor_message(self, node, removed):
        """Return warning text to display if removed contributor is the user
        who authorized the App addon
        """
        if self.user_settings and self.user_settings.owner == removed:
            # TODO
            pass

    # backwards compatibility
    before_remove_contributor = before_remove_contributor_message

    def after_register(self, node, registration, user, save=True):
        """After registering a node, copy the user settings and save the
        chosen folder.

        :return: A tuple of the form (cloned_settings, message)
        """
        return None, ''

    def after_fork(self, node, fork, user, save=True):
        """After forking, copy user settings if the user is the one who authorized
        the addon.

        :return: A tuple of the form (cloned_settings, message)
        """
        return None, ''

    def after_remove_contributor(self, node, removed):
        """If the removed contributor was the user who authorized the App
        addon, remove the auth credentials from this node.
        Return the message text that will be displayed to the user.
        """
        if self.user_settings and self.user_settings.owner == removed:
            self.user_settings = None
            self.save()
            name = removed.fullname
            url = node.web_url_for('node_setting')
            return ('Because the Application add-on for this project was authenticated'
                    'by {name}, authentication information has been deleted. You '
                    'can re-authenticate on the <a href="{url}">Settings</a> page'
                    ).format(**locals())
