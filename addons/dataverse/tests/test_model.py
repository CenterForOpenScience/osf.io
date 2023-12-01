from nose.tools import *  # noqa
import mock
import pytest
import unittest

from tests.base import get_default_metaschema
from framework.auth.decorators import Auth

from addons.base.tests.models import (OAuthAddonNodeSettingsTestSuiteMixin,
                                      OAuthAddonUserSettingTestSuiteMixin)

from addons.dataverse.models import NodeSettings
from addons.dataverse.tests.factories import (
    DataverseAccountFactory, DataverseNodeSettingsFactory,
    DataverseUserSettingsFactory
)
from addons.dataverse.tests import utils
from osf_tests.factories import DraftRegistrationFactory
from api_tests.addons_tests.dataverse.test_configure_dataverse import mock_dataverse_client

pytestmark = pytest.mark.django_db


class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, utils.DataverseAddonTestCase, unittest.TestCase):

    short_name = 'dataverse'
    full_name = 'Dataverse'
    ExternalAccountFactory = DataverseAccountFactory

    NodeSettingsFactory = DataverseNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = DataverseUserSettingsFactory

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            '_dataset_id': '1234567890',
            'dataset_doi': '10.123/DAVATERSE',
            'owner': self.node
        }

    @mock.patch('website.archiver.tasks.archive')
    def test_does_not_get_copied_to_registrations(self, mock_archive):
        registration = self.node.register_node(
            schema=get_default_metaschema(),
            auth=Auth(user=self.node.creator),
            draft_registration=DraftRegistrationFactory(branched_from=self.node),
        )
        assert_false(registration.has_addon('dataverse'))

    ## Overrides ##

    def test_create_log(self):
        action = 'file_added'
        filename = 'pizza.nii'
        nlog = self.node.logs.count()
        self.node_settings.create_waterbutler_log(
            auth=Auth(user=self.user),
            action=action,
            metadata={'path': filename, 'materialized': filename},
        )
        self.node.reload()
        assert_equal(self.node.logs.count(), nlog + 1)
        assert_equal(
            self.node.logs.latest().action,
            '{0}_{1}'.format(self.short_name, action),
        )
        assert_equal(
            self.node.logs.latest().params['filename'],
            filename
        )

    @mock.patch('addons.dataverse.client.Connection', return_value=mock_dataverse_client())
    def test_set_folder(self, mock_client):
        dataset = utils.create_mock_dataset()
        dataverse = utils.create_mock_dataverse()

        self.node_settings.set_folder(dataverse, dataset=dataset, auth=Auth(self.user))
        # Folder was set
        assert_equal(self.node_settings.folder_id, dataset.id)
        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_dataset_linked'.format(self.short_name))

    def test_serialize_credentials(self):
        credentials = self.node_settings.serialize_waterbutler_credentials()

        assert_is_not_none(self.node_settings.external_account.oauth_secret)
        expected = {'token': self.node_settings.external_account.oauth_secret}
        assert_equal(credentials, expected)

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'host': self.external_account.oauth_key,
            'doi': self.node_settings.dataset_doi,
            'id': self.node_settings.dataset_id,
            'name': self.node_settings.dataset,
        }
        assert_equal(settings, expected)


class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'dataverse'
    full_name = 'Dataverse'
    ExternalAccountFactory = DataverseAccountFactory
