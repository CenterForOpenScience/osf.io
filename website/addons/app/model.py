# -*- coding: utf-8 -*-
"""Persistence layer for the app addon.
"""
import os

from modularodm import fields

from website.addons.base import lookup
from website.search.search import update_metadata

from framework import Guid, GuidStoredObject


class AppNodeSettings(GuidStoredObject):

    redirect_mode = 'proxy'
    _id = fields.StringField(primary=True)

    custom_routes = fields.DictionaryField()
    allow_queries = fields.BooleanField(default=False)
    allow_public_read = fields.BooleanField(default=True)

    def _guid_to_metadata(self, guid):
        """Resolve a Guid to a metadata object
        :param guid (str, Guid) The guid to attach data to
        :return Metadata
        """
        if isinstance(guid, Guid):
            return guid[self]
        else:
            return Guid.load(guid)[self]

    def _ensure_types(self, blob):
        types = self.schema
        if not types:
            return

        for key, val in blob.items():
            if not types.get(key):
                continue

            if isinstance(val, list):

                for index in val:
                    if not isinstance(index, types.get(key)):
                        raise ValueError
                continue

            if isinstance(val, types.get(key)):
                continue

            raise ValueError

    @property
    def schema(self):
        pass

    @property
    def deep_url(self):
        return os.path.join(self.owner.deep_url, 'app')

    @property
    def name(self):
        # Todo possibly store this for easier querying
        return self.owner.title

    @property
    def namespace(self):
        return self._id

    @property
    def all_data(self):
        return self.metadata__data

    def get_data(self, guid):
        return self._guid_to_metadata(guid)

    def attach_data(self, guid, data):
        """Attach a dictionary to the specified guid under this applications
        namespace.
        :param guid (str, Guid) The guid to attach data to
        :param data dict The metadata to store
        """
        self._ensure_types(data)

        metastore = self._guid_to_metadata(guid)
        metastore.update(data)
        metastore.save()

        update_metadata(metastore)

    def delete_data(self, guid, key=None):
        metadata = self._guid_to_metadata(guid)
        if key:
            del metadata[key]
            metadata.save()
        else:
            metadata.remove()

    def __setitem__(self, route, query):
        self.custom_routes[route] = query
        self.save()

    def __getitem__(self, url):
        return self.custom_routes[url]

    def __delitem__(self, url):
        del self.custom_routes[url]
        self.save()

    def get(self, url, default=None):
        return self.custom_routes.get(url, default)

    ##### Addon Settings methods #####

    # Had to be copied and not inherited to use a guid for humans

    deleted = fields.BooleanField(default=False)
    owner = fields.ForeignField('node', backref='addons')

    def delete(self, save=True):
        self.deleted = True
        if save:
            self.save()

    def undelete(self, save=True):
        self.deleted = False
        if save:
            self.save()

    def render_config_error(self, data):
        # Note: `config` is added to `self` in `AddonConfig::__init__`.
        template = lookup.get_template('project/addon/config_error.mako')
        return template.get_def('config_error').render(
            title=self.config.full_name,
            name=self.config.short_name,
            **data
        )

    def to_json(self, user):
        return {
            'addon_short_name': self.config.short_name,
            'addon_full_name': self.config.full_name,
            'user': {
                'permissions': self.owner.get_permissions(user)
            },
            'node': {
                'id': self.owner._id,
                'api_url': self.owner.api_url,
                'url': self.owner.url,
                'is_registration': self.owner.is_registration,
            },
            'application_url': '/api/v1/%s/' % self._id
        }

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

    # Need to implement these so we can be a faux addon
    def before_page_load(self, node, user):
        pass

    def before_make_public(self, node):
        pass

    def before_make_private(self, node):
        pass

    def after_set_privacy(self, node, permissions):
        pass

    def after_delete(self, node, user):
        pass
