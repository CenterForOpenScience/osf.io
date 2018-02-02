import pytest

from tests.json_api_test_app import JSONAPITestApp
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory
)


@pytest.mark.django_db
class TestRegistrationFilesList(object):

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(
            project=self.node, creator=self.user)
        # Note: folders/files added to node do not seem to get picked up by the
        # Registration factory so they are added after
        self.folder = self.registration.get_addon(
            'osfstorage').get_root().append_folder('Archive of OSF Storage')
        self.folder.save()
        self.file = self.folder.append_file(
            'So, on average, it has been super comfortable this week')
        self.file.save()

    def test_registration_relationships_contains_guid_not_id(self):
        url = '/{}registrations/{}/files/{}/'.format(
            API_BASE, self.registration._id, self.file.provider)
        res = self.app.get(url, auth=self.user.auth)

        split_href = res.json['data'][0]['relationships']['files']['links']['related']['href'].split(
            '/')
        assert self.registration._id in split_href
        assert self.registration.id not in split_href
