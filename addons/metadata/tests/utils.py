# -*- coding: utf-8 -*-
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from .. import SHORT_NAME


class BaseAddonTestCase(AddonTestCase):
    ADDON_SHORT_NAME = SHORT_NAME
    OWNERS = ['node']
    NODE_USER_FIELD = None
    ExternalAccountFactory = None
    Provider = None
    Serializer = None
    client = None

    def set_node_settings(self, settings):
        return
