# -*- coding: utf-8 -*-
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase


class JupyterhubAddonTestCase(AddonTestCase):
    ADDON_SHORT_NAME = 'jupyterhub'
    OWNERS = ['node']
    NODE_USER_FIELD = None
    ExternalAccountFactory = None
    Provider = None
    Serializer = None
    client = None

    def set_node_settings(self, settings):
        return
