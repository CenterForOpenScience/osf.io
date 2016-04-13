# -*- coding: utf-8 -*-
from website.addons.base.testing import OAuthAddonTestCaseMixin, AddonTestCase
from website.addons.s3.provider import S3Provider
from website.addons.s3.serializer import S3Serializer
from website.addons.s3.tests.factories import S3AccountFactory

class S3AddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 's3'
    ExternalAccountFactory = S3AccountFactory
    Provider = S3Provider
    Serializer = S3Serializer
    client = None
    folder = 'bucket'
