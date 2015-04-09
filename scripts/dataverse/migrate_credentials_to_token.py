#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to migrate dataverse username/password to API token.

"""

import logging
from modularodm import Q
import requests

import mock
from nose.tools import *
from tests.base import OsfTestCase
from tests.factories import UserFactory

from website.app import init_app
from scripts import utils as script_utils

from website.addons.dataverse.model import AddonDataverseUserSettings
from website.addons.dataverse.settings import HOST

logger = logging.getLogger(__name__)


def do_migration(records, dry=True):
    for record in records:

        logger.info('Record found for user {}'.format(record.dataverse_username))

        # Generate API token from username/password
        url = 'http://{0}/api/bulitin-users/{1}/api-token?password={2}'.format(
            HOST, record.dataverse_username, record.dataverse_password
        )
        resp = requests.get(url)
        token = resp.json()['data']['message']

        logger.info('setting token to {}'.format(token))

        if not dry:
            record.api_token = token
            record.dataverse_username = None
            record.dataverse_password = None

            record.save()


def get_targets():
    return AddonDataverseUserSettings.find(
        Q('dataverse_username', 'ne', None) &
        Q('encrypted_password', 'ne', None)
    )


def main(dry=True):
    init_app(set_backends=True, routes=False, mfr=False)  # Sets the storage backends on all models
    do_migration(get_targets(), dry=dry)


class TestCredentialsMigration(OsfTestCase):

    def setUp(self):
        super(TestCredentialsMigration, self).setUp()
        self.user = UserFactory()
        self.user.add_addon('dataverse')
        self.user_addon = self.user.get_addon('dataverse')
        self.user_addon.save()

    @mock.patch('requests.get')
    def test_migration(self, mock_get):
        mock_resp = mock.create_autospec(requests.Response)
        mock_resp.json.return_value = {
            u'data': {u'message': u'12345-67890'},
            u'status': u'OK',
        }
        mock_get.return_value = mock_resp

        do_migration([self.user_addon], dry=False)
        self.user_addon.reload()

        assert_equal(self.user_addon.api_token, '12345-67890')
        assert_is_none(self.user_addon.dataverse_username)
        assert_is_none(self.user_addon.dataverse_password)

    def test_get_targets(self):
        AddonDataverseUserSettings.remove()
        addons = [
            AddonDataverseUserSettings(),
            AddonDataverseUserSettings(dataverse_username='username'),
            AddonDataverseUserSettings(dataverse_password='secret'),
            AddonDataverseUserSettings(dataverse_username='username', dataverse_password='secret'),
        ]
        for addon in addons:
            addon.save()
        targets = get_targets()
        assert_equal(targets.count(), 1)
        assert_equal(targets[0]._id, addons[-1]._id)


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)