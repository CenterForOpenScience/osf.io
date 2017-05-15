# -*- coding: utf-8 -*-
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.azureblobstorage.provider import AzureBlobStorageProvider
from addons.azureblobstorage.serializer import AzureBlobStorageSerializer
from addons.azureblobstorage.tests.factories import AzureBlobStorageAccountFactory

class AzureBlobStorageAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'azureblobstorage'
    ExternalAccountFactory = AzureBlobStorageAccountFactory
    Provider = AzureBlobStorageProvider
    Serializer = AzureBlobStorageSerializer
    client = None
    folder = {
    	'path': 'container',
    	'name': 'container',
    	'id': 'container'
	}
