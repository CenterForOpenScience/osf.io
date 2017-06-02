# -*- coding: utf-8 -*-
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.swift.provider import SwiftProvider
from addons.swift.serializer import SwiftSerializer
from addons.swift.tests.factories import SwiftAccountFactory

class SwiftAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'swift'
    ExternalAccountFactory = SwiftAccountFactory
    Provider = SwiftProvider
    Serializer = SwiftSerializer
    client = None
    folder = {
    	'path': 'container',
    	'name': 'container',
    	'id': 'container'
	}
