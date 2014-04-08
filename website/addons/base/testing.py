# -*- coding: utf-8 -*-

from framework.auth.decorators import Auth
from tests.base import DbTestCase
from tests.factories import AuthUserFactory, ProjectFactory

class AddonTestCase(DbTestCase):
    """General Addon TestCase that automatically sets up a user and node with
    an addon.

    Must define:

        - ADDON_SHORT_NAME (class variable)
        - create_app(self): Returns a webtest app
        - set_user_settings(self, settings): Method that makes any modifications
            to the UserSettings object, e.g. setting access_token
        - set_node_settings(self, settings): Metehod that makes any modifications
            to the NodeSettings object.

    This will give you:

        - self.user: A User with the addon enabled
        - self.project: A project created by self.user and has the addon enabled
        - self.user_settings: AddonUserSettings object for the addon
        - self.node_settings: AddonNodeSettings object for the addon
        - self.app: A webtest app.
    """

    ADDON_SHORT_NAME = None

    # Optional overrides
    def create_user(self):
        return AuthUserFactory()

    def create_project(self):
        return ProjectFactory(creator=self.user)

    # Required abstract methods
    def create_app(self):
        raise NotImplementedError('Must define create_app(self) method.')

    def set_user_settings(self, settings):
        """Make any necessary modifications to the user settings object,
        e.g. setting access_token.
        """
        raise NotImplementedError('Must define set_user_settings(self, settings) method')

    def set_node_settings(self, settings):
        raise NotImplementedError('Must define set_node_settings(self, settings) method')

    def setUp(self):
        self.app = self.create_app()
        self.user = self.create_user()
        if not self.ADDON_SHORT_NAME:
            raise ValueError('Must define ADDON_SHORT_NAME in the test class.')
        self.user.add_addon(self.ADDON_SHORT_NAME, override=True)
        assert self.user.has_addon(self.ADDON_SHORT_NAME), '{0} is not enabled'.format(self.ADDON_SHORT_NAME)
        self.user.save()

        self.user_settings = self.user.get_addon(self.ADDON_SHORT_NAME)
        self.set_user_settings(self.user_settings)
        self.user_settings.save()

        self.project = self.create_project()
        self.project.add_addon(self.ADDON_SHORT_NAME, auth=Auth(self.user))
        self.project.save()
        self.node_settings = self.project.get_addon(self.ADDON_SHORT_NAME)
        # User has imported their addon settings to this node
        self.node_settings.user_settings = self.user_settings
        self.set_node_settings(self.node_settings)
        self.node_settings.save()
