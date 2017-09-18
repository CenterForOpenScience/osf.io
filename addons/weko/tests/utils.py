# -*- coding: utf-8 -*-
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.weko.models import WEKOProvider
from addons.weko.serializer import WEKOSerializer
from addons.weko.tests.factories import WEKOAccountFactory


class ConnectionMock(object):
    def get_login_user(self):
        return None


class WEKOAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'weko'
    ExternalAccountFactory = WEKOAccountFactory
    Provider = WEKOProvider
    Serializer = WEKOSerializer
    client = None
    folder = {
    	'path': 'container',
    	'name': 'container',
    	'id': 'container'
	}
