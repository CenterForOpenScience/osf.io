import pytest
from framework.auth import Auth
from osf_tests.factories import ProjectFactory, InstitutionFactory, RegionFactory

from addons.osfstorage.apps import osf_storage_root
from addons.osfstorage.tests import factories
from addons.osfstorage.tests.utils import StorageTestCase

@pytest.mark.django_db
class TestNonInstitutionalNodeSettings(StorageTestCase):
    def setUp(self):
        super(TestNonInstitutionalNodeSettings, self).setUp()
        self.user = factories.AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.institution = InstitutionFactory()
        self.osfstorage = self.node.get_addon('osfstorage')

    def test_fields(self):
        assert self.osfstorage._id
        assert self.osfstorage.has_auth is True
        assert self.osfstorage.complete is True

    def test_root(self):
        auth = Auth(user=self.user)
        assert osf_storage_root(None, self.osfstorage, auth) is not None

@pytest.mark.django_db
class TestInstitutionalNodeSettings(StorageTestCase):
    def setUp(self):
        super(TestInstitutionalNodeSettings, self).setUp()
        self.user = factories.AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.institution = InstitutionFactory()
        self.osfstorage = self.node.get_addon('osfstorage')
        new_region = RegionFactory(
            _id=self.institution._id,
            name='Institutional Storage',
            waterbutler_settings={'disabled': True}
        )
        self.osfstorage.region = new_region
        self.osfstorage.save()

    def test_fields(self):
        assert self.osfstorage._id
        assert self.osfstorage.has_auth is False
        assert self.osfstorage.complete is False

    def test_root(self):
        auth = Auth(user=self.user)
        assert osf_storage_root(None, self.osfstorage, auth) is None
