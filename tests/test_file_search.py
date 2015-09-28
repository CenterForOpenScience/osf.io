import mock
import time
from nose.tools import *

from tests.base import OsfTestCase
from tests import factories
from website.addons.osfstorage.model import OsfStorageFileNode
from website.addons.osfstorage import settings as osfstorage_settings
from website.search import file_search
from website.search import search
from website.search.elastic_search import es, INDEX

from website import settings

TEST_INDEX = 'test'


def get_count(doc_type):
    return es.count(index=TEST_INDEX, doc_type=doc_type)['count']


class FileSearchTestCase(OsfTestCase):
    def setUp(self):
        search.delete_index(TEST_INDEX)
        search.create_index(TEST_INDEX)
        settings.USE_FILE_INDEXING = True

    def tearDown(self):
        search.delete_index(TEST_INDEX)
        settings.USE_FILE_INDEXING = False


class TestIndexDoc(FileSearchTestCase):
    def setUp(self):
        super(TestIndexDoc, self).setUp()
        self.test_doc_body = {
            'name': 'the_spanish_inqusition.pdf',
            'path': 'a0123456789',
            'parent': 'fak7e',
            'attachment': '123456789abcdefg',
            'category': 'file',
        }
        self.file_path = 'a0123456789'
        self.parent_guid = 'fak7e'

    def test_index_document(self):
        assert_equal(get_count('project_file'), 0)
        file_search.index_doc(
            self.file_path,
            self.parent_guid,
            'project_file',
            self.test_doc_body,
            index=TEST_INDEX,
        )
        time.sleep(1)
        assert_equal(get_count('project_file'), 1)


class TestDeleteDoc(FileSearchTestCase):
    def setUp(self):
        super(TestDeleteDoc, self).setUp()
        self.test_doc_body = {
            'name': 'the_spanish_inqusition.pdf',
            'path': 'a0123456789',
            'parent': 'fak7e',
            'attachment': '123456789abcdefg',
            'category': 'file',
        }
        self.file_path = 'a0123456789'
        self.parent_guid_one = 'fak7e'
        self.parent_guid_two = 'fak3r'

        file_search.index_doc(
            self.file_path,
            self.parent_guid_one,
            'project_file',
            self.test_doc_body,
            index=TEST_INDEX,
        )

        file_search.index_doc(
            self.file_path,
            self.parent_guid_two,
            'project_file',
            self.test_doc_body,
            index=TEST_INDEX,
        )
        time.sleep(1)

    def test_delete_one_document(self):
        assert_equal(get_count('project_file'), 2)
        file_search.delete_doc(
            id=self.file_path,
            parent_id=self.parent_guid_one,
            doc_type='project_file',
            index=TEST_INDEX,
        )
        time.sleep(1)
        assert_equal(get_count('project_file'), 1)

    def test_delete_two_document(self):
        assert_equal(get_count('project_file'), 2)
        file_search.delete_doc(
            id=self.file_path,
            parent_id=self.parent_guid_one,
            doc_type='project_file',
            index=TEST_INDEX,
        )

        file_search.delete_doc(
            id=self.file_path,
            parent_id=self.parent_guid_two,
            doc_type='project_file',
            index=TEST_INDEX,
        )

        time.sleep(1)
        assert_equal(get_count('project_file'), 0)


class TestUpdateTo(FileSearchTestCase):
    def setUp(self):
        super(TestUpdateTo, self).setUp()
        self.user = factories.AuthUserFactory()
        self.project_node = factories.ProjectFactory(creator=self.user)

        self.osfstorage = self.project_node.get_addon('osfstorage')
        self.root_node = self.osfstorage.root_node
        self.file = self.root_node.append_file('spam_and_eggs.txt')

        self.file.create_version(
            self.user,
            {
                'object': '06d80e',
                'service': 'cloud',
                osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
            },
            {
                'size': 1337,
                'contentType': 'text/txt',
            }
        ).save()

        settings.USE_FILE_INDEXING = True

    def tearDown(self):
        super(TestUpdateTo, self).tearDown()
        settings.USE_FILE_INDEXING = False

    def test_update_to_project_file(self):
        with mock.patch('website.search.file_util.get_file_content_url', lambda fn: 'http://fake_url.com/'):
            self.project_node.set_privacy('public')

        assert_equal(get_count(doc_type='project_file'), 0)
        file_search.update_to(self.file, self.project_node, "Spam spam spam spam!", index=TEST_INDEX)
        time.sleep(1)
        assert_equal(get_count(doc_type='project_file'), 1)


class TestDeleteFrom(FileSearchTestCase):
    def setUp(self):
        super(TestDeleteFrom, self).setUp()
        self.user = factories.AuthUserFactory()
        self.project_node = factories.ProjectFactory(creator=self.user)

        self.osfstorage = self.project_node.get_addon('osfstorage')
        self.root_node = self.osfstorage.root_node
        self.file = self.root_node.append_file('spam_and_eggs.txt')

        self.file.create_version(
            self.user,
            {
                'object': '06d80e',
                'service': 'cloud',
                osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
            },
            {
                'size': 1337,
                'contentType': 'text/txt',
            }
        ).save()

    def test_delete_from(self):
        with mock.patch('website.search.file_util.get_file_content_url', lambda fn: 'http://fake_url.com/'):
            self.project_node.set_privacy('public')

        file_search.update_to(
            self.file,
            self.project_node,
            "the spanish inqusition",
            index=TEST_INDEX,
        )
        time.sleep(1)
        assert_equal(get_count('project_file'), 1)
        file_search.delete_from(
            self.file,
            self.project_node,
            index=TEST_INDEX,
        )

        time.sleep(1)
        assert_equal(get_count('project_file'), 0)


class TestRetrieve(FileSearchTestCase):
    def setUp(self):
        super(TestRetrieve, self).setUp()
        self.test_file_body = {
            'name': 'the_spanish_inqusition.pdf',
            'path': 'a0123456789',
            'parent': 'fak7e',
            'attachment': '123456789abcdefg',
            'category': 'file',
        }
        self.file_path = 'a0123456789'
        self.parent_guid = 'fak7e'

    def test_retrieve(self):
        file_search.index_doc(
            self.file_path,
            self.parent_guid,
            'project_file',
            self.test_file_body,
            index=TEST_INDEX,
        )
        time.sleep(1)
        assert_equal(get_count('project_file'), 1)

        retrieved_body = file_search.retrieve(
            self.file_path,
            self.parent_guid,
            'project_file',
            index=TEST_INDEX,
        )

        assert_equal(self.test_file_body, retrieved_body)

    def test_unable_to_retrieve(self):
        retrieved_body = file_search.retrieve(
            self.file_path,
            self.parent_guid,
            'project_file',
            index=TEST_INDEX,
        )
        assert_false(retrieved_body)
