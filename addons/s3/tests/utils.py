# -*- coding: utf-8 -*-
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.s3.tests.factories import S3AccountFactory
from addons.s3.provider import S3Provider
from addons.s3.serializer import S3Serializer

class S3AddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 's3'
    ExternalAccountFactory = S3AccountFactory
    Provider = S3Provider
    Serializer = S3Serializer
    client = None
    folder = {
        'path': 'bucket',
        'name': 'bucket',
        'id': 'bucket'
    }
