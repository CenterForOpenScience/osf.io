import pytest
from addons.base.utils import get_mfr_url

from addons.osfstorage.tests.utils import StorageTestCase
from tests.base import OsfTestCase
from osf_tests.factories import ProjectFactory, UserFactory, RegionFactory, CommentFactory
from website.settings import MFR_SERVER_URL


class MockFolder(dict, object):

    def __init__(self):
        self.name = 'Fake Folder'
        self.json = {'id': 'Fake Key', 'parent_id': 'cba321', 'name': 'Fake Folder'}
        self['data'] = {'name': 'Fake Folder', 'key': 'Fake Key', 'parentCollection': False}
        self['library'] = {'type': 'personal', 'id': '34241'}
        self['name'] = 'Fake Folder'
        self['id'] = 'Fake Key'


class MockLibrary(dict, object):

    def __init__(self):
        self.name = 'Fake Library'
        self.json = {'id': 'Fake Library Key', 'parent_id': 'cba321'}
        self['data'] = {'name': 'Fake Library', 'key': 'Fake Key', 'id': '12345' }
        self['name'] = 'Fake Library'
        self['id'] = 'Fake Library Key'


@pytest.mark.django_db
class TestAddonsUtils(OsfTestCase):
    def test_mfr_url(self):
        user = UserFactory()
        project = ProjectFactory(creator=user)
        comment = CommentFactory()
        assert get_mfr_url(project, 'github') == MFR_SERVER_URL
        assert get_mfr_url(project, 'osfstorage') == project.osfstorage_region.mfr_url
        assert get_mfr_url(comment, 'osfstorage') == MFR_SERVER_URL
