# -*- coding: utf-8 -*-
from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth

from website import settings

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory


class AddonTestCase(OsfTestCase):
    """General Addon TestCase that automatically sets up a user and node with
    an addon.

    Must define:

        - ADDON_SHORT_NAME (class variable)
        - set_user_settings(self, settings): Method that makes any modifications
            to the UserSettings object, e.g. setting access_token
        - set_node_settings(self, settings): Metehod that makes any modifications
            to the NodeSettings object.

    This will give you:

        - self.user: A User with the addon enabled
        - self.project: A project created by self.user and has the addon enabled
        - self.user_settings: AddonUserSettings object for the addon
        - self.node_settings: AddonNodeSettings object for the addon

    """
    DB_NAME = getattr(settings, 'TEST_DB_ADDON_NAME', 'osf_addon')
    ADDON_SHORT_NAME = None
    OWNERS = ['user', 'node']
    NODE_USER_FIELD = 'user_settings'

    # Optional overrides
    def create_user(self):
        return AuthUserFactory.build()

    def create_project(self):
        return ProjectFactory(creator=self.user)

    def set_user_settings(self, settings):
        """Make any necessary modifications to the user settings object,
        e.g. setting access_token.

        """
        raise NotImplementedError('Must define set_user_settings(self, settings) method')

    def set_node_settings(self, settings):
        raise NotImplementedError('Must define set_node_settings(self, settings) method')

    def create_user_settings(self):
        """Initialize user settings object if requested by `self.OWNERS`.

        """
        if 'user' not in self.OWNERS:
            return
        self.user.add_addon(self.ADDON_SHORT_NAME, override=True)
        assert self.user.has_addon(self.ADDON_SHORT_NAME), '{0} is not enabled'.format(self.ADDON_SHORT_NAME)
        self.user_settings = self.user.get_addon(self.ADDON_SHORT_NAME)
        self.set_user_settings(self.user_settings)
        self.user_settings.save()

    def create_node_settings(self):
        """Initialize node settings object if requested by `self.OWNERS`,
        additionally linking to user settings if requested by
        `self.NODE_USER_FIELD`.

        """
        if 'node' not in self.OWNERS:
            return
        self.project.add_addon(self.ADDON_SHORT_NAME, auth=Auth(self.user))
        self.node_settings = self.project.get_addon(self.ADDON_SHORT_NAME)
        # User has imported their addon settings to this node
        if self.NODE_USER_FIELD:
            setattr(self.node_settings, self.NODE_USER_FIELD, self.user_settings)
        self.set_node_settings(self.node_settings)
        self.node_settings.save()

    def setUp(self):

        super(AddonTestCase, self).setUp()

        self.user = self.create_user()
        if not self.ADDON_SHORT_NAME:
            raise ValueError('Must define ADDON_SHORT_NAME in the test class.')
        self.user.save()

        self.project = self.create_project()
        self.project.save()

        self.create_user_settings()
        self.create_node_settings()

class OAuthAddonTestCaseMixin(object):

    @property
    def ExternalAccountFactory(self):
        raise NotImplementedError()

    def set_user_settings(self, settings):
        self.external_account = self.ExternalAccountFactory()
        self.external_account.save()
        self.user.external_accounts.append(self.external_account)
        self.user.save()
        self.auth = Auth(self.user)

    def set_node_settings(self, settings):
        self.user_settings.grant_oauth_access(self.project, self.external_account)
