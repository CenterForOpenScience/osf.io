from nose.tools import *
import mock

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.dataverse.model import AddonDataverseUserSettings, \
    AddonDataverseNodeSettings

class TestCallbacks(DbTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()

        self.project = ProjectFactory.build()
        self.project.save()

    def test_user_settings(self):
        # Create user settings
        dataverse = AddonDataverseUserSettings()
        creator = self.project.creator

        # Dataverse is not authorized by default
        assert_false(dataverse.to_json(creator)['authorized'])

        # If there is a user, dataverse is authorized
        dataverse.dataverse_username = 'snowman'
        assert_true(dataverse.to_json(creator)['authorized'])
        assert_equals(dataverse.to_json(creator)['authorized_dataverse_user'],
                      'snowman')
