# -*- coding: utf-8 -*-
from webtest_plus import TestApp

import website
from website.addons.base.testing import AddonTestCase


class ForwardAddonTestCase(AddonTestCase):

    ADDON_SHORT_NAME = 'forward'

    OWNERS = ['node']
    NODE_USER_FIELD = None

    def set_user_settings(self, settings):
        pass

    def set_node_settings(self, settings):
        settings.url = 'http://frozen.pizza.reviews/'
