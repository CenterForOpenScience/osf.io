# -*- coding: utf-8 -*-
"""Persistence layer for the app addon.
"""

from modularodm import fields

from framework import Guid, GuidStoredObject

from website.addons.base import AddonNodeSettingsBase


class AppNodeSettings(GuidStoredObject, AddonNodeSettingsBase):

    allow_queries = fields.BooleanField(default=False)
    allow_public_read = fields.BooleanField(default=True)
    custom_routes = fields.DictionaryField()

    @property
    def name(self):
        return self.owner.title

    @property
    def namespace(self):
        return self._id

    def add_custom_route(self, route, map_to):
        self.custom_routes[route] = map_to

    def attach_data(self, guid, data):
        """Attach a dictionary to the specified guid under this applications
        namespace.
        :param guid (str, Guid) The guid to attach data to
        :param data dict The metadata to store
        """
        metastore = self._guid_to_metadata(guid)

        metastore.update(data)
        metastore.save()

    def _guid_to_metadata(self, guid):
        if isinstance(guid, Guid):
            return guid.metadata[self.namespace]
        else:
            return Guid.load(guid).metadata[self.namespace]

    def get_data(self, guid):
        return self._guid_to_metadata(guid)

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
