# -*- coding: utf-8 -*-
from addons.base.tests.base import AddonTestCase


class ForwardAddonTestCase(AddonTestCase):

    ADDON_SHORT_NAME = 'forward'

    OWNERS = ['node']
    NODE_USER_FIELD = None

    def set_user_settings(self, settings):
        pass

    def set_node_settings(self, settings):
        settings.url = 'http://frozen.pizza.reviews/'
