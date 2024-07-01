from django.conf import settings as django_settings

from framework.auth import Auth
from osf_tests.factories import AuthUserFactory, ProjectFactory


class AddonTestCase:
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
    DISABLE_OUTGOING_CONNECTIONS = True
    DB_NAME = getattr(django_settings, 'TEST_DB_ADDON_NAME', 'osf_addon')
    ADDON_SHORT_NAME = None
    OWNERS = ['user', 'node']
    NODE_USER_FIELD = 'user_settings'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_settings = None
        self.project = None
        self.user = None
        self.user_settings = None

    # Optional overrides
    @staticmethod
    def create_user():
        return AuthUserFactory.build()

    def create_project(self):
        return ProjectFactory(creator=self.user)

    def set_user_settings(self, settings):
        raise NotImplementedError('Must define set_user_settings(self, settings) method')

    def set_node_settings(self, settings):
        raise NotImplementedError('Must define set_node_settings(self, settings) method')

    def create_user_settings(self):
        """Initialize user settings object if requested by `self.OWNERS`.
        """
        if 'user' not in self.OWNERS:
            return
        self.user.add_addon(self.ADDON_SHORT_NAME)
        assert self.user.has_addon(self.ADDON_SHORT_NAME), f'{self.ADDON_SHORT_NAME} is not enabled'
        self.user_settings = self.user.get_addon(self.ADDON_SHORT_NAME)
        self.set_user_settings(self.user_settings)
        self.user_settings.save()

    def create_node_settings(self):
        """Initialize node settings object if requested by `self.OWNERS`,
        additionally linking to user settings if requested by `self.NODE_USER_FIELD`.
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

        super().setUp()

        self.user = self.create_user()
        if not self.ADDON_SHORT_NAME:
            raise ValueError('Must define ADDON_SHORT_NAME in the test class.')
        self.user.save()
        self.project = self.create_project()
        self.project.save()
        self.create_user_settings()
        self.create_node_settings()


class OAuthAddonTestCaseMixin:

    @property
    def ExternalAccountFactory(self):
        raise NotImplementedError()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth = None
        self.external_account = None
        self.project = None
        self.user_settings = None
        self.user = None

    def set_user_settings(self, settings):
        self.external_account = self.ExternalAccountFactory()
        self.external_account.save()
        self.user.external_accounts.add(self.external_account)
        self.user.save()
        self.auth = Auth(self.user)

    def set_node_settings(self, settings):
        self.user_settings.grant_oauth_access(self.project, self.external_account)
