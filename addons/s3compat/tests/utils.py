# -*- coding: utf-8 -*-
from nose.tools import (assert_equals, assert_true, assert_false)

from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.s3compat.tests.factories import S3CompatAccountFactory
from addons.s3compat.provider import S3CompatProvider
from addons.s3compat.serializer import S3CompatSerializer
from addons.s3compat import utils

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

    def test_https(self):
        connection = utils.connect_s3compat(host='securehost',
                                            access_key='a',
                                            secret_key='s')
        assert_true(connection.is_secure)
        assert_equals(connection.host, 'securehost')
        assert_equals(connection.port, 443)

        connection = utils.connect_s3compat(host='securehost:443',
                                            access_key='a',
                                            secret_key='s')
        assert_true(connection.is_secure)
        assert_equals(connection.host, 'securehost')
        assert_equals(connection.port, 443)

    def test_http(self):
        connection = utils.connect_s3compat(host='normalhost:80',
                                            access_key='a',
                                            secret_key='s')
        assert_false(connection.is_secure)
        assert_equals(connection.host, 'normalhost')
        assert_equals(connection.port, 80)

        connection = utils.connect_s3compat(host='normalhost:8080',
                                            access_key='a',
                                            secret_key='s')
        assert_false(connection.is_secure)
        assert_equals(connection.host, 'normalhost')
        assert_equals(connection.port, 8080)
