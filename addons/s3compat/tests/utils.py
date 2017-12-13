# -*- coding: utf-8 -*-
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.s3compat.tests.factories import S3CompatAccountFactory
from addons.s3compat.provider import S3CompatProvider
from addons.s3compat.serializer import S3CompatSerializer

class S3CompatAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 's3compat'
    ExternalAccountFactory = S3CompatAccountFactory
    Provider = S3CompatProvider
    Serializer = S3CompatSerializer
    client = None
    folder = {
        'path': 'bucket',
        'name': 'bucket',
        'id': 'bucket'
    }
