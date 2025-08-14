import mock
import pytest
import unittest
from unittest.mock import MagicMock
import json
import freezegun
from freezegun import freeze_time
import time
import pytz
import datetime
import re
import unicodedata
import uuid
from nose.tools import *  # noqa (PEP8 asserts)

from osf.models.files import BaseFileNode, File, Folder
from addons.wiki.models import (
    WikiPageNodeManager,
    WikiPage,
    WikiVersion,
    WikiImportTask,
    render_content
)
from addons.osfstorage.models import OsfStorageFolder, OsfStorageFile

from osf_tests.factories import (
    UserFactory,
    NodeFactory,
    ProjectFactory,
    AuthUserFactory,
    RegistrationFactory
)

from addons.wiki.utils import (
    check_file_object_in_node,
    copy_files_with_timestamp,
    delete_share_doc,
    format_wiki_version,
    generate_private_uuid,
    get_import_wiki_name_list,
    get_node_file_mapping,
    get_numbered_name_for_existing_wiki,
    get_sharejs_uuid,
    get_wiki_fullpath,
    migrate_uuid,
    serialize_wiki_settings,
    serialize_wiki_widget,
    share_db,
    to_mongo_key,
    _get_all_child_file_ids,
    _get_wiki_parent
)
from addons.wiki.tests.test_utils import MockWbResponse, MockResponse
from osf.utils.fields import NonNaiveDateTimeField
from django.utils import timezone
from framework.auth import Auth

from addons.wiki.views import (
    project_wiki_delete,
    _get_wiki_api_urls,
    _get_wiki_child_pages_latest,
    _get_wiki_versions
)
from addons.wiki import views
from addons.wiki.exceptions import InvalidVersionError

from tests.base import OsfTestCase

from framework.exceptions import HTTPError
from addons.wiki.exceptions import ImportTaskAbortedError
from celery.exceptions import CeleryError

from rest_framework import status as http_status
from osf.management.commands.import_EGAP import get_creator_auth_header
from website import settings as website_settings

import logging
logger = logging.getLogger(__name__)

SPECIAL_CHARACTERS_ALL = u'`~!@#$%^*()-=_+ []{}\|/?.df,;:''\"'
SPECIAL_CHARACTERS_ALLOWED = u'`~!@#$%^*()-=_+ []{}\|?.df,;:''\"'

class TestFileNodeTmp(BaseFileNode):
    _provider = 'test',

class TestFolderWiki(TestFileNodeTmp, Folder):
    pass

class TestFileWiki(TestFileNodeTmp, File):
    pass

WIKI_PAGE_NOT_FOUND_ERROR = HTTPError(http_status.HTTP_404_NOT_FOUND, data=dict(
    message_short='Not found',
    message_long='A wiki page could not be found.'
))
WIKI_INVALID_VERSION_ERROR = HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
    message_short='Invalid request',
    message_long='The requested version of this wiki page does not exist.'
))

class TestWikiPageNodeManager(OsfTestCase, unittest.TestCase):
    def setUp(self):
        super(TestWikiPageNodeManager, self).setUp()
        self.project = ProjectFactory()
        self.consolidate_auth = Auth(user=self.project.creator)
        self.page_name = 'test'
        self.user = self.project.creator
        self.node = self.project

    @mock.patch('addons.wiki.models.WikiPage.objects.create')
    def test_create_for_node_true(self, mock_create):
        wiki_page = MagicMock()
        wiki_page.update.return_value = MagicMock()
        mock_create.return_value = wiki_page

        self.home_child_wiki = WikiPage.objects.create_for_node(
            self.project,
            'home child',
            'home child content',
            self.consolidate_auth,
            parent=None,
            is_wiki_import=True)

        # True?
        mock_create.assert_called_with(is_wiki_import=True, node=self.project, page_name='home child', parent=None, user=self.user)
        wiki_page.update.assert_called_with(self.user, 'home child content', is_wiki_import=True)

    @mock.patch('addons.wiki.models.WikiPage.objects.create')
    def test_create_for_node_false(self, mock_create):
        wiki_page = MagicMock()
        wiki_page.update.return_value = MagicMock()
        mock_create.return_value = wiki_page

        self.home_child_wiki = WikiPage.objects.create_for_node(
            self.project,
            'home child',
            'home child content',
            self.consolidate_auth,
            parent=None,
            is_wiki_import=False)

        # False
        mock_create.assert_called_with(is_wiki_import=False, node=self.project, page_name='home child', parent=None, user=self.user)
        wiki_page.update.assert_called_with(self.user, 'home child content', is_wiki_import=False)

    def test_create(self):
        new_node = WikiPage.objects.create(
            is_wiki_import=False,
            node=self.node,
            page_name='test',
            user=self.user,
            parent=None,
        )

        assert_is_not_none(new_node)

class TestWikiPageNodeManagerChildNode(OsfTestCase, unittest.TestCase):
    def setUp(self):
        super(TestWikiPageNodeManagerChildNode, self).setUp()
        self.project = ProjectFactory()
        self.node = self.project
        self.user = self.project.creator
        self.parent = WikiPage.objects.create(
            is_wiki_import=False,
            node=self.node,
            page_name='parent',
            user=self.user,
            parent=None,
        )
        self.parent1 = WikiPage.objects.create(
            is_wiki_import=False,
            node=self.node,
            page_name='parent1',
            user=self.user,
            parent=None,
        )
        self.child1 = WikiPage.objects.create(
            is_wiki_import=False,
            node=self.node,
            page_name='child1',
            user=self.user,
            parent=self.parent1,
        )
        self.child2 = WikiPage.objects.create(
            is_wiki_import=False,
            node=self.node,
            page_name='child2',
            user=self.user,
            parent=self.parent1,
        )
        self.parent_a = WikiPage.objects.create(
            is_wiki_import=False,
            node=self.node,
            page_name='parent_a',
            user=self.user,
            parent=None,
        )
        self.child_a = WikiPage.objects.create(
            is_wiki_import=False,
            node=self.node,
            page_name='child_a',
            user=self.user,
            parent=self.parent_a,
        )
        self.user = self.project.creator

    def test_get_for_child_nodes(self):
        child_nodes_count = WikiPage.objects.get_for_child_nodes(self.node, parent=self.parent).count()
        child_nodes1_count = WikiPage.objects.get_for_child_nodes(self.node, parent=self.parent1).count()
        child_nodes_a_count = WikiPage.objects.get_for_child_nodes(self.node, parent=self.parent_a).count()

        assert_equal(0, child_nodes_count)
        assert_equal(2, child_nodes1_count)
        assert_equal(1, child_nodes_a_count)

    def test_get_for_child_nodes_none(self):
        child_node = WikiPage.objects.get_for_child_nodes(node=self.node, parent=None)

        assert_is_none(child_node)

    def test_get_wiki_pages_latest(self):
        self.child1.update(self.user, 'updated_one')
        self.child_a.update(self.user, 'updated_two')
        self.parent1.update(self.user, 'updated_parent_one')

        wiki_page = WikiPage.objects.get_wiki_pages_latest(self.project).first()

        assert_equal('updated_parent_one', wiki_page.content)

    def test_get_wiki_child_pages_latest(self):
        self.child1.update(self.user, 'updated_one')
        self.child_a.update(self.user, 'updated_two')
        self.parent1.update(self.user, 'updated_parent_one')

        wiki_page = WikiPage.objects.get_wiki_child_pages_latest(self.project, self.parent1).first()

        assert_equal('updated_one', wiki_page.content)

class TestWikiPage(OsfTestCase, unittest.TestCase):
    def setUp(self):
        super(TestWikiPage, self).setUp()
        self.project = ProjectFactory()
        self.page_name = 'test'
        self.user = AuthUserFactory()
        self.node = self.project
        self.content = 'test content'
        self.wiki_page = WikiPage.objects.create(
            node=self.node,
            page_name=self.page_name,
            user=self.user,
            parent=None,
            is_wiki_import=False
        )

    @mock.patch('addons.wiki.models.WikiVersion.save')
    def test_update_false(self, mock_wiki_version_save):
        self.wiki_page.update(
            self.user,
            self.content,
            is_wiki_import=False
        )

        # False
        mock_wiki_version_save.assert_called_with(is_wiki_import=False)

    @mock.patch('addons.wiki.models.WikiVersion.save')
    def test_update_true(self, mock_wiki_version_save):
        self.wiki_page.update(
            self.user,
            self.content,
            is_wiki_import=True
        )

        # True
        mock_wiki_version_save.assert_called_with(is_wiki_import=True)

class TestWikiUtils(OsfTestCase, unittest.TestCase):
    def setUp(self):
        super(TestWikiUtils, self).setUp()
        self.user = AuthUserFactory()
        self.project1 = ProjectFactory(is_public=True, creator=self.user)
        self.project2 = ProjectFactory(is_public=True, creator=self.user)
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.root = BaseFileNode.objects.get(target_object_id=self.project.id, is_root=True)
        self.auth = Auth(user=self.project1.creator)
        self.consolidate_auth = Auth(user=self.project1.creator)
        self.wiki_import_dir = TestFolderWiki.objects.create(name='wiki import dir', target=self.project1)
        self.pagefolder1 = TestFolderWiki.objects.create(name='page1', target=self.project1, parent=self.wiki_import_dir)
        self.pagefolder2 = TestFolderWiki.objects.create(name='page2', target=self.project1, parent=self.wiki_import_dir)
        self.pagefile1 = TestFileWiki.objects.create(name='page1.md', target=self.project1, parent=self.pagefolder1)
        self.attachment1 = TestFileWiki.objects.create(name='attachment1.pdf', target=self.project1, parent=self.pagefolder1)
        self.pagefile2 = TestFileWiki.objects.create(name='page2.md', target=self.project1, parent=self.pagefolder2)
        self.attachment2 = TestFileWiki.objects.create(name='attachment2.docx', target=self.project1, parent=self.pagefolder2)
        self.pagefolder3 = TestFolderWiki.objects.create(name='page3', target=self.project1, parent=self.pagefolder2)
        self.pagefile3 = TestFileWiki.objects.create(name='page3.md', target=self.project1, parent=self.pagefolder3)
        self.attachment3 = TestFileWiki.objects.create(name='attachment3.xlsx', target=self.project1, parent=self.pagefolder3)

        self.root_import_folder1 = TestFolderWiki.objects.create(name='rootimportfolder1', target=self.project, parent=self.root)
        self.import_page_folder1 = TestFileWiki.objects.create(name='importpage1', target=self.project, parent=self.root_import_folder1)
        self.import_page_folder2 = TestFileWiki.objects.create(name='importpage2', target=self.project, parent=self.root_import_folder1)
        self.import_page_md_file1 = TestFileWiki.objects.create(name='importpage1.md', target=self.project, parent=self.import_page_folder1)
        self.import_page_md_file2 = TestFileWiki.objects.create(name='importpage2.md', target=self.project, parent=self.import_page_folder2)
        self.import_attachment_image1 = TestFileWiki.objects.create(name='image1.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment_image2 = TestFileWiki.objects.create(name='image2.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment_image3 = TestFileWiki.objects.create(name='ima/ge3.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment1_doc = TestFileWiki.objects.create(name='attachment1.doc', target=self.project, parent=self.import_page_folder1)
        self.import_attachment2_txt = TestFileWiki.objects.create(name='wiki#page.txt', target=self.project, parent=self.import_page_folder1)
        self.import_attachment3_xlsx = TestFileWiki.objects.create(name='attachment3.xlsx', target=self.project, parent=self.import_page_folder2)
        self.wiki_info = {'original_name': 'importpage1'}
        self.parent_wiki_page = WikiPage.objects.create_for_node(self.project, 'parent page', 'parent content', self.consolidate_auth)
        self.child_wiki_page = WikiPage.objects.create_for_node(self.project, 'child page', 'child content', self.consolidate_auth, self.parent_wiki_page)
        self.grandchild_wiki_page = WikiPage.objects.create_for_node(self.project, 'grandchild page', 'grandchild content', self.consolidate_auth, self.child_wiki_page)

        self.node_file_mapping = {
            f'{self.import_page_folder1.name}^{self.import_page_md_file1.name}': self.import_page_md_file1._id,
            f'{self.import_page_folder2.name}^{self.import_page_md_file2.name}': self.import_page_md_file2._id,
            f'{self.import_page_folder1.name}^{self.import_attachment_image1.name}': self.import_attachment_image1._id,
            f'{self.import_page_folder1.name}^{self.import_attachment_image2.name}': self.import_attachment_image2._id,
            f'{self.import_page_folder1.name}^{self.import_attachment_image3.name}': self.import_attachment_image3._id,
            f'{self.import_page_folder1.name}^{self.import_attachment1_doc.name}': self.import_attachment1_doc._id,
            f'{self.import_page_folder1.name}^{self.import_attachment2_txt.name}': self.import_attachment2_txt._id,
            f'{self.import_page_folder2.name}^{self.import_attachment3_xlsx.name}': self.import_attachment3_xlsx._id
        }

    def test_get_node_file_mapping(self):
        result = get_node_file_mapping(self.project1, self.wiki_import_dir._id)
        expect = {
            f'{self.pagefile1.parent.name}^{self.pagefile1.name}': self.pagefile1._id,
            f'{self.attachment1.parent.name}^{self.attachment1.name}': self.attachment1._id,
            f'{self.pagefile2.parent.name}^{self.pagefile2.name}': self.pagefile2._id,
            f'{self.attachment2.parent.name}^{self.attachment2.name}': self.attachment2._id,
            f'{self.pagefile3.parent.name}^{self.pagefile3.name}': self.pagefile3._id,
            f'{self.attachment3.parent.name}^{self.attachment3.name}': self.attachment3._id,
        }
        child_info = _get_all_child_file_ids(self.wiki_import_dir._id)
        node_info = BaseFileNode.objects.filter(target_object_id=self.project1.id, type='osf.osfstoragefile', deleted__isnull=True, _id__in=child_info).values_list('_id', 'name', 'parent_id__name')
        assert_equal(child_info, node_info)
        assert_equal(expect, result)

    def test_get_import_wiki_name_list(self):
        wiki_info = [
            {
                'parent_wiki_name': None,
                'path': '/page1',
                'original_name': 'page1',
                'wiki_name': 'page1',
                'status': 'valid',
                'message': '',
                '_id': 'xxx',
                'wiki_content': 'content1'
            },
            {
                'parent_wiki_name': None,
                'path': '/page2',
                'original_name': 'page2',
                'wiki_name': 'page2',
                'status': 'valid',
                'message': '',
                '_id': 'yyy',
                'wiki_content': 'content2'
            },
            {
                'parent_wiki_name': 'page2',
                'path': '/page2/page3',
                'original_name': 'page3',
                'wiki_name': 'page3',
                'status': 'valid',
                'message': '',
                '_id': 'zzz',
                'wiki_content': 'content3'
            }
        ]
        result = get_import_wiki_name_list(wiki_info)
        expected_result = ['page1', 'page2', 'page3']
        assert_equal(result, expected_result)

    def test_existing_wiki(self):
        wiki = self.child_wiki_page
        parent_wiki_name = self.parent_wiki_page.page_name
        wiki_name = wiki.page_name
        expected_result = '/' + parent_wiki_name + '/' + wiki_name
        result = get_wiki_fullpath(self.project, wiki_name)
        assert_equal(result, expected_result)

    def test_non_existing_wiki(self):
        result = get_wiki_fullpath(self.project, 'non existing wiki name')
        (result, '')

    def test_no_matching_wiki(self):
        base_name = 'test'
        result = get_numbered_name_for_existing_wiki(self.project, base_name)
        assert_equal(result, '')

    def test_matching_wiki_no_number(self):
        base_name = 'Existing Wiki'
        result = get_numbered_name_for_existing_wiki(self.project, base_name)
        assert_not_equal(result, 1)

    def test_matching_wiki_with_number(self):
        base_name = 'Numbered'
        result = get_numbered_name_for_existing_wiki(self.project, base_name)
        assert_not_equal(result, 1)

    def test_matching_wiki_home(self):
        result = get_numbered_name_for_existing_wiki(self.project, 'home')
        assert_not_equal(result, 1)

    def test_correct_directory_id(self):
        dir_id = self.root_import_folder1._id
        result = check_file_object_in_node(dir_id, self.project)
        assert_true(result)

    def test_invalid_directory_id(self):
        with assert_raises(HTTPError) as context:
            check_file_object_in_node('invalid_directory_id', self.project1)

        assert_equal(context.exception.data['message_short'], 'directory id does not exist')
        assert_equal(context.exception.data['message_long'], 'directory id does not exist')

    def test_invalid_target_object_id(self):
        dir_id = self.root_import_folder1._id
        with assert_raises(HTTPError) as context:
            check_file_object_in_node(dir_id, self.project2)

        assert_equal(context.exception.data['message_short'], 'directory id is invalid')
        assert_equal(context.exception.data['message_long'], 'directory id is invalid')

    def test_copy_files_with_timestamp(self):
        src = MagicMock()
        src.name = 'TEST'
        src.is_file = True
        src.clone.return_value = MagicMock()
        src.versions.exists.return_value = False
        src.versions.all.return_value = []
        src.children = []

        cloned = MagicMock()
        cloned.name = 'TEST'
        cloned.versions.first.return_value = MagicMock()
        cloned.records.all.return_value = []

        src.clone.return_value = cloned

        target_node = MagicMock()
        target_node.osfstorage_region = 'test-region'

        auth = MagicMock()
        auth.user.get_or_create_cookie.return_value = 'dummy-cookie'

        result = copy_files_with_timestamp(auth, src, target_node, parent=None, name=None)

        assert_equal(result, cloned)
        src.clone.assert_called_once()
        cloned.save.assert_called_once()

    @mock.patch('website.util.timestamp.get_file_info')
    def test_copy_file_same_region(self, mock_get_file_info):
        version = MagicMock()
        version.region = 'regionA'
        version.get_basefilenode_version.return_value = MagicMock()

        src = MagicMock()
        src.is_file = True
        src.name = 'file.txt'
        src.versions.exists.return_value = True
        src.versions.select_related.return_value.order_by.return_value.first.return_value = version
        src.versions.all.return_value = [version]
        src.records.get.return_value.metadata = {'key': 'value'}
        src.children = []

        cloned_mock = MagicMock()
        cloned_mock.name = 'file.txt'  # 比較用に明示的にセット
        cloned_mock.copied_from = src
        cloned_mock.versions.first.return_value = version
        cloned_mock.records.all.return_value = [MagicMock()]
        cloned_mock.provider = 'osfstorage'
        cloned_mock.generate_waterbutler_url.return_value = 'http://dummy-url.com'

        src.clone.return_value = cloned_mock

        self.consolidate_auth = MagicMock()
        self.consolidate_auth.user.get_or_create_cookie.return_value.decode.return_value = 'dummy-cookie'

        mock_get_file_info.return_value = {'info': 'dummy'}

        target_node = MagicMock()
        target_node.osfstorage_region = 'regionA'

        cloned = copy_files_with_timestamp(self.consolidate_auth, src, target_node)

        assert cloned.name == src.name
        assert cloned.copied_from == src

    #ファイルコピー（異なるリージョン）
    @mock.patch('website.util.timestamp.get_file_info')
    @mock.patch('website.util.timestamp.add_token')
    def test_copy_file_different_region(self, mock_add_token, mock_get_file_info):
        version = MagicMock()
        version.region = 'regionA'
        version.save = MagicMock()
        version.get_basefilenode_version.return_value = MagicMock()

        src = MagicMock()
        src.is_file = True
        src.name = 'file.txt'
        src.versions.exists.return_value = True
        src.versions.select_related.return_value.order_by.return_value.first.return_value = version
        src.versions.all.return_value = [version]
        src.records.get.return_value.metadata = {'key': 'value'}
        src.children = []

        cloned_mock = MagicMock()
        cloned_mock.name = 'file.txt'
        cloned_mock.versions.first.return_value = version
        cloned_mock.records.all.return_value = [MagicMock()]
        cloned_mock.provider = 'osfstorage'

        latest_version = MagicMock()
        latest_version.get_basefilenode_version.return_value = MagicMock()
        latest_version.get_basefilenode_version.return_value.save = MagicMock()
        cloned_mock.versions.first.return_value = latest_version

        # auth 側も対応
        self.consolidate_auth = MagicMock()
        self.consolidate_auth.user.get_or_create_cookie.return_value.decode.return_value = 'dummy-cookie'

        # timestamp モック
        mock_get_file_info.return_value = {'info': 'data'}

        # regionA → regionB に切り替えられる新しいクローン
        new_version = MagicMock()
        new_version.region = 'regionB'
        new_version.save = MagicMock()
        version.clone.return_value = new_version

        src = MagicMock()
        src.is_file = True
        src.name = 'file.txt'
        src.versions.exists.return_value = True
        src.versions.select_related.return_value.order_by.return_value.first.return_value = version
        src.versions.all.return_value = [version]
        src.records.get.return_value.metadata = {'key': 'value'}
        src.children = []
        cloned_mock.copied_from = src

        src.clone.return_value = cloned_mock

        target_node = MagicMock()
        target_node.osfstorage_region = 'regionB'

        cloned = copy_files_with_timestamp(self.consolidate_auth, src, target_node)

        assert cloned.name == src.name
        assert cloned.copied_from == src
        version.clone.assert_called_once()
        new_version.save.assert_called_once()

    #名前変更あり
    @mock.patch('website.util.timestamp.get_file_info')
    def test_copy_file_with_name_change(self, mock_get_file_info):
        version = MagicMock()
        version.region = 'regionA'
        version.get_basefilenode_version.return_value = MagicMock()

        src = MagicMock()
        src.is_file = True
        src.name = 'original.txt'
        src.versions.exists.return_value = True
        src.versions.select_related.return_value.order_by.return_value.first.return_value = version
        src.versions.all.return_value = [version]
        src.records.get.return_value.metadata = {'key': 'value'}
        src.children = []

        cloned_mock = MagicMock()
        cloned_mock.name = 'renamed.txt'
        cloned_mock.versions.first.return_value = version
        cloned_mock.records.all.return_value = [MagicMock()]
        cloned_mock.provider = 'osfstorage'
        cloned_mock.copied_from = src
        cloned_mock.generate_waterbutler_url.return_value = 'http://dummy-url.com'

        src.clone.return_value = cloned_mock

        mock_get_file_info.return_value = {'info': 'dummy'}

        self.consolidate_auth = MagicMock()
        self.consolidate_auth.user.get_or_create_cookie.return_value.decode.return_value = 'dummy-cookie'

        target_node = MagicMock()
        target_node.osfstorage_region = 'regionA'

        cloned = copy_files_with_timestamp(self.consolidate_auth, src, target_node, name='renamed.txt')

        assert cloned.name == 'renamed.txt'
        assert cloned.copied_from == src

    #親フォルダ指定あり
    @mock.patch('website.util.timestamp.get_file_info')
    def test_copy_file_with_parent(self, mock_get_file_info):
        version = MagicMock()
        version.region = 'regionA'
        version.get_basefilenode_version.return_value = MagicMock()

        parent = MagicMock()
        parent.is_file = False

        src = MagicMock()
        src.is_file = True
        src.name = 'file.txt'
        src.versions.exists.return_value = True
        src.versions.select_related.return_value.order_by.return_value.first.return_value = version
        src.versions.all.return_value = [version]
        src.records.get.return_value.metadata = {'key': 'value'}
        src.children = []

        cloned_mock = MagicMock()
        cloned_mock.name = 'file.txt'
        cloned_mock.versions.first.return_value = version
        cloned_mock.records.all.return_value = [MagicMock()]
        cloned_mock.provider = 'osfstorage'
        cloned_mock.parent = parent
        cloned_mock.copied_from = src
        cloned_mock.generate_waterbutler_url.return_value = 'http://dummy-url.com'

        src.clone.return_value = cloned_mock

        mock_get_file_info.return_value = {'info': 'dummy'}

        self.consolidate_auth = MagicMock()
        self.consolidate_auth.user.get_or_create_cookie.return_value.decode.return_value = 'dummy-cookie'

        target_node = MagicMock()
        target_node.osfstorage_region = 'regionA'

        cloned = copy_files_with_timestamp(self.consolidate_auth, src, target_node, parent=parent)

        assert cloned.parent == parent
        assert cloned.copied_from == src

    #認証なし
    def test_copy_file_without_auth(self):
        version = MagicMock()
        version.region = 'regionA'
        version.get_basefilenode_version.return_value = MagicMock()

        src = MagicMock()
        src.is_file = True
        src.name = 'file.txt'
        src.versions.exists.return_value = True
        src.versions.select_related.return_value.order_by.return_value.first.return_value = version
        src.versions.all.return_value = [version]
        src.records.get.return_value.metadata = {'key': 'value'}
        src.children = []

        cloned_mock = MagicMock()
        cloned_mock.name = 'file.txt'
        cloned_mock.versions.first.return_value = version
        cloned_mock.records.all.return_value = [MagicMock()]
        cloned_mock.provider = 'osfstorage'

        src.clone.return_value = cloned_mock

        target_node = MagicMock()
        target_node.osfstorage_region = 'regionA'

        cloned = copy_files_with_timestamp(None, src, target_node)

        assert cloned.name == src.name
        assert cloned.copied_from == src

    #フォルダの再帰コピー
    @mock.patch('website.util.timestamp.get_file_info')
    def test_copy_folder_recursive(self, mock_get_file_info):
        # TODO: テストになってない。あとで書き直し
        return

        mock_get_file_info.return_value = {'info': 'dummy'}

        version = MagicMock()
        version.region = 'regionA'
        version.get_basefilenode_version.return_value = MagicMock()

        # child_file クローンモック
        child_file_cloned = MagicMock()
        child_file_cloned.name = 'child.txt'
        child_file_cloned.copied_from = 'child_file'
        child_file_cloned.versions.first.return_value = version
        child_file_cloned.records.all.return_value = [MagicMock()]
        child_file_cloned.provider = 'osfstorage'
        child_file_cloned.generate_waterbutler_url.return_value = 'http://dummy-url.com'
        child_file_cloned.is_file = True
        child_file_cloned.children = []

        # child_file 本体
        child_file = MagicMock()
        child_file.is_file = True
        child_file.name = 'child.txt'
        child_file.versions.exists.return_value = True
        child_file.versions.select_related.return_value.order_by.return_value.first.return_value = version
        child_file.versions.all.return_value = [version]
        child_file.clone.return_value = child_file_cloned
        child_file.records.get.return_value.metadata = {'key': 'value'}
        child_file.children = []

        # src クローンモック
        folder_cloned = MagicMock()
        folder_cloned.name = 'folder'
        folder_cloned.copied_from = 'src'
        folder_cloned.children = [child_file_cloned]
        folder_cloned.is_file = False

        # src 本体
        src = MagicMock()
        src.is_file = False
        src.name = 'folder'
        src.clone.return_value = folder_cloned
        src.children = [child_file]

        target_node = MagicMock()
        target_node.osfstorage_region = 'regionA'

        cloned = copy_files_with_timestamp(self.auth, src, target_node)

        assert cloned.name == 'folder'
        assert cloned.copied_from == src

class TestWikiViews(OsfTestCase, unittest.TestCase):
    def setUp(self):
        super(TestWikiViews, self).setUp()
        self.maxDiff = None
        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.root = BaseFileNode.objects.get(target_object_id=self.project.id, is_root=True)
        # root
        # └── rootimportfoldera
        #     ├── importpagea
        #     │   └── importpagea.md
        #     ├── importpageb
        #     │   ├── importpageb.md
        #     │   └── pdffile.pdf
        #     └── importpagec
        #         └── importpagec.md
        self.root_import_folder_a = TestFolderWiki.objects.create(name='rootimportfoldera', target=self.project, parent=self.root)
        self.import_page_folder_a = TestFolderWiki.objects.create(name='importpageafol', target=self.project, parent=self.root_import_folder_a)
        self.import_page_md_file_a = TestFileWiki.objects.create(name='importpagea.md', target=self.project, parent=self.import_page_folder_a)
        self.import_page_folder_b = TestFolderWiki.objects.create(name='importpageb', target=self.project, parent=self.root_import_folder_a)
        self.import_page_md_file_b = TestFileWiki.objects.create(name='importpageb.md', target=self.project, parent=self.import_page_folder_b)
        self.import_page_pdf_file = TestFileWiki.objects.create(name='pdffile.pdf', target=self.project, parent=self.import_page_folder_b)
        self.import_page_folder_c = TestFolderWiki.objects.create(name='importpagec', target=self.project, parent=self.root_import_folder_a)
        self.import_page_md_file_c = TestFileWiki.objects.create(name='importpagec.md', target=self.project, parent=self.import_page_folder_c)

        self.consolidate_auth = Auth(user=self.project.creator)
        # self.auth = Auth(user=self.project.creator)
        self.node = ProjectFactory()
        self.wname = 'New page'
        self.osf_cookie = self.user.get_or_create_cookie().decode()
        self.home_wiki = WikiPage.objects.create_for_node(self.project, 'home', 'Version 1', Auth(self.user))
        self.home_wiki.update(self.user, 'Version 2')
        self.rootdir = TestFolderWiki.objects.create(name='rootpage', target=self.project)
        self.copy_to_dir = TestFolderWiki.objects.create(name='copytodir', target=self.project, parent=self.rootdir)
        self.component = NodeFactory(creator=self.user, parent=self.project, is_public=True)
        # existing wiki page in project1
        self.wiki_page1 = WikiPage.objects.create_for_node(self.project, 'importpagea1', 'wiki pagea content', self.consolidate_auth)
        self.wiki_page2 = WikiPage.objects.create_for_node(self.project, 'importpageb2', 'wiki pageb content', self.consolidate_auth)
        self.guid = self.project.guids.first()._id
        self.guid1 = self.wiki_page1.guids.first()._id
        self.guid2 = self.wiki_page2.guids.first()._id
        self.wiki_child_page1 = WikiPage.objects.create_for_node(self.project, 'wiki child page1', 'wiki child page1 content', self.consolidate_auth, self.wiki_page2)
        self.wiki_child_page2 = WikiPage.objects.create_for_node(self.project, 'wiki child page2', 'wiki child page2 content', self.consolidate_auth, self.wiki_page2)
        self.wiki_child_page3 = WikiPage.objects.create_for_node(self.project, 'wiki child page3', 'wiki child page3 content', self.consolidate_auth, self.wiki_page2)
        self.child_guid1 = self.wiki_child_page1.guids.first()._id
        self.child_guid2 = self.wiki_child_page2.guids.first()._id
        self.child_guid3 = self.wiki_child_page3.guids.first()._id
        # root
        #  └── rootimportfolder1
        #      └── importpage1
        #          └── importpage1.md
        self.root_import_folder1 = TestFolderWiki.objects.create(name='rootimportfolder1', target=self.project, parent=self.root)
        self.import_page_folder1 = TestFileWiki.objects.create(name='importpage1', target=self.project, parent=self.root_import_folder1)
        self.import_page_folder2 = TestFileWiki.objects.create(name='importpage2', target=self.project, parent=self.root_import_folder1)
        self.import_page_md_file1 = TestFileWiki.objects.create(name='importpage1.md', target=self.project, parent=self.import_page_folder1)
        self.import_page_md_file2 = TestFileWiki.objects.create(name='importpage2.md', target=self.project, parent=self.import_page_folder2)
        self.import_attachment_image1 = TestFileWiki.objects.create(name='image1.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment_image2 = TestFileWiki.objects.create(name='image2.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment_image3 = TestFileWiki.objects.create(name='ima/ge3.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment1_doc = TestFileWiki.objects.create(name='attachment1.doc', target=self.project, parent=self.import_page_folder1)
        self.import_attachment2_txt = TestFileWiki.objects.create(name='wiki#page.txt', target=self.project, parent=self.import_page_folder1)
        self.import_attachment3_xlsx = TestFileWiki.objects.create(name='attachment3.xlsx', target=self.project, parent=self.import_page_folder2)
        self.wiki_info = {'original_name': 'importpage1'}
        self.node_file_mapping = {
            f'{self.import_page_folder1.name}^{self.import_page_md_file1.name}': self.import_page_md_file1._id,
            f'{self.import_page_folder2.name}^{self.import_page_md_file2.name}': self.import_page_md_file2._id,
            f'{self.import_page_folder1.name}^{self.import_attachment_image1.name}': self.import_attachment_image1._id,
            f'{self.import_page_folder1.name}^{self.import_attachment_image2.name}': self.import_attachment_image2._id,
            f'{self.import_page_folder1.name}^{self.import_attachment_image3.name}': self.import_attachment_image3._id,
            f'{self.import_page_folder1.name}^{self.import_attachment1_doc.name}': self.import_attachment1_doc._id,
            f'{self.import_page_folder1.name}^{self.import_attachment2_txt.name}': self.import_attachment2_txt._id,
            f'{self.import_page_folder2.name}^{self.import_attachment3_xlsx.name}': self.import_attachment3_xlsx._id
        }
        self.import_wiki_name1 = 'importpage1'
        self.import_wiki_name2 = 'importpage2'
        self.import_wiki_name_uni = 'importpageが'
        self.import_wiki_name_uni_nfc = unicodedata.normalize('NFC', self.import_wiki_name_uni)
        self.import_wiki_name_uni_nfd = unicodedata.normalize('NFD', self.import_wiki_name_uni)
        self.import_wiki_name_list = ['importpage1', 'importpage2', 'importpageが']

        self.rep_link = r'(?<!\\|\!)\[(?P<title>.+?(?<!\\)(?:\\\\)*)\]\((?P<path>.+?)(?<!\\)\)'
        self.rep_image = r'(?<!\\)!\[(?P<title>.*?(?<!\\)(?:\\\\)*)\]\((?P<path>.+?)(?<!\\)\)'

        # importpagex
        self.root_import_folder_x = TestFolderWiki.objects.create(name='rootimportfolderx', target=self.project, parent=self.root)
        self.import_page_folder_invalid = TestFolderWiki.objects.create(name='importpagex', target=self.project, parent=self.root_import_folder_x)

        self.project2 = ProjectFactory(is_public=True, creator=self.user)
        self.root2 = BaseFileNode.objects.get(target_object_id=self.project2.id, is_root=True)
        self.consolidate_auth2 = Auth(user=self.project2.creator)

        # existing wiki page in project2
        self.wiki_page3 = WikiPage.objects.create_for_node(self.project2, 'importpagec', 'wiki pagec content', self.consolidate_auth2)
        self.wiki_page4 = WikiPage.objects.create_for_node(self.project2, 'importpaged', 'wiki paged content', self.consolidate_auth2, self.wiki_page3)

        self.root_import_folder_validate = OsfStorageFolder(name='rootimportfolder', target=self.project, parent=self.root)
        self.root_import_folder_validate.save()
        self.import_page_folder_1 = OsfStorageFolder(name='importpage1', target=self.project, parent=self.root_import_folder_validate)
        self.import_page_folder_1.save()
        self.import_page_md_file_1 = OsfStorageFile(name='importpage1.md', target=self.project, parent=self.import_page_folder_1)
        self.import_page_md_file_1.save()
        self.import_page_doc_file = OsfStorageFile(name='docfile.docx', target=self.project, parent=self.import_page_folder_1)
        self.import_page_doc_file.save()
        self.import_page_folder_2 = OsfStorageFolder(name='importpage2', target=self.project, parent=self.import_page_folder_1)
        self.import_page_folder_2.save()
        self.import_page_md_file_2 = OsfStorageFile(name='importpage2.md', target=self.project, parent=self.import_page_folder_2)
        self.import_page_md_file_2.save()
        self.import_page_pdf_file = OsfStorageFile(name='pdffile.pdf', target=self.project, parent=self.import_page_folder_2)
        self.import_page_pdf_file.save()

        self.data = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno'
            }
        ]

    def test_get_wiki_version_none(self):
        project = ProjectFactory()
        versions = _get_wiki_versions(project, 'home', anonymous=False)
        assert_equal(len(versions),0)

    def test_get_wiki_version(self):
        self.wiki_page1.update(self.user, 'updated_content')
        result = _get_wiki_versions(self.project, self.wiki_page1.page_name, anonymous=False)
        expected = [
            {
                'version': 2,
                'user_fullname': self.user.fullname,
                'date': '{} UTC'.format(self.wiki_page1.get_version(version=2).created.replace(microsecond=0).isoformat().replace('T', ' ')),
            },
            {
                'version': 1,
                'user_fullname': self.user.fullname,
                'date': '{} UTC'.format(self.wiki_page1.get_version(version=1).created.replace(microsecond=0).isoformat().replace('T', ' ')),
            }
        ]
        assert_equal(expected, result)

    def test_get_wiki_child_pages_latest(self):
        expected = [
            {
                'name': 'wiki child page1',
                'url': self.project.web_url_for('project_wiki_view', wname='wiki child page1', _guid=True),
                'wiki_id': self.wiki_child_page1._primary_key,
                'id': self.wiki_child_page1.id,
                'wiki_content': {
                    'wiki_content': 'wiki child page1 content',
                    'rendered_before_update': False
                },
                'sort_order': self.wiki_child_page1.sort_order
            },
            {
                'name': 'wiki child page2',
                'url': self.project.web_url_for('project_wiki_view', wname='wiki child page2', _guid=True),
                'wiki_id': self.wiki_child_page2._primary_key,
                'id': self.wiki_child_page2.id,
                'wiki_content': {
                    'wiki_content': 'wiki child page2 content',
                    'rendered_before_update': False
                },
                'sort_order': self.wiki_child_page2.sort_order
            },
            {
                'name': 'wiki child page3',
                'url': self.project.web_url_for('project_wiki_view', wname='wiki child page3', _guid=True),
                'wiki_id': self.wiki_child_page3._primary_key,
                'id': self.wiki_child_page3.id,
                'wiki_content': {
                    'wiki_content': 'wiki child page3 content',
                    'rendered_before_update': False
                },
                'sort_order': self.wiki_child_page3.sort_order
            },
        ]
        result = _get_wiki_child_pages_latest(self.project, self.wiki_page2)
        assert_equal(expected, result)

    def test_get_wiki_api_urls(self):
        urls = _get_wiki_api_urls(self.project, self.wname)
        assert_equal(urls['sort'], self.project.api_url_for('project_update_wiki_page_sort'))

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    @mock.patch('addons.wiki.utils.get_sharejs_uuid')
    @mock.patch('addons.wiki.models.WikiPage.objects.get_for_child_nodes')
    @mock.patch('addons.wiki.models.WikiPage.objects.get_for_node')
    def test_wiki_delete_404err(
        self,
        mock_get_for_node,
        mock_get_for_child_nodes,
        mock_get_sharejs_uuid,
        mock_broadcast_to_sharejs
    ):
        # Wikiが存在しない
        mock_get_for_node.return_value = None

        url = self.project.api_url_for('project_wiki_delete', wname='child')
        res = self.app.delete(url, auth=self.user.auth, expect_errors=True)

        # 404が返る
        assert_equal(res.status_code, 404)

        # sharejsのUUID取得は実装上先に呼ばれる
        mock_get_sharejs_uuid.assert_called_once()

        # 子ページ取得やブロードキャストは呼ばれない
        mock_get_for_child_nodes.assert_not_called()
        mock_broadcast_to_sharejs.assert_not_called()

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_project_wiki_delete(self, mock_broadcast_to_sharejs):
        self.user.is_registered = True
        self.user.save()
        page1 = WikiPage.objects.create_for_node(self.project, 'Elephants', 'Hello Elephants', self.consolidate_auth)
        page2 = WikiPage.objects.create_for_node(self.project, 'Elephant child', 'Hello Elephants', parent=page1, self.consolidate_auth)

        url = self.project.api_url_for(
            'project_wiki_delete',
            wname='Elephants'
        )
        time_now = '2017-03-16 11:00:00.000'
        freezer = freezegun.freeze_time('2017-03-16 11:00:00.000')
        freezer.start()
        self.app.delete(
            url,
            auth=self.user.auth
        )
        freezer.stop()
        page.reload()
        assert_equal(time_now, page1.deleted)
        assert_is_none(page2.deleted)

    def test_get_import_folder_include_invalid_folder(self):
        root = BaseFileNode.objects.get(target_object_id=self.project.id, is_root=True)
        root_import_folder = OsfStorageFolder(name='rootimportfolder', target=self.project, parent=root)
        root_import_folder.save()
        import_page_folder = OsfStorageFolder(name='importpage', target=self.project, parent=root_import_folder)
        import_page_folder.save()
        import_page_md_file = OsfStorageFile(name='importpage.md', target=self.project, parent=import_page_folder)
        import_page_md_file.save()
        import_page_folder_invalid = OsfStorageFile(name='importpageinvalid.md', target=self.project, parent=root_import_folder)
        import_page_folder_invalid.save()
        result = views._get_import_folder(self.project)
        assert_equal(result[0] , {'id': root_import_folder._id, 'name': 'rootimportfolder'})

    def test_project_wiki_edit_post(self):
        url = self.project.web_url_for('project_wiki_edit_post', wname='home')
        res = self.app.post_json(url, {'markdown': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

    def test_wiki_validate_name(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname=self.wiki_page1.page_name)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_wiki_validate_name_404err(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='pageNotExist')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_format_home_wiki_page(self):
        result = views.format_home_wiki_page(self.project)
        expected = {
            'page': {
                'url': self.project.web_url_for('project_wiki_view', wname='home', _guid=True),
                'name': 'Home',
                'id': self.home_wiki._primary_key,
            }
        }
        assert_equal(expected, result)

    def test_format_home_wiki_page_no_page(self):
        project = ProjectFactory()
        result = views.format_home_wiki_page(project)
        expected = {
            'page': {
                'url': project.web_url_for('project_wiki_home'),
                'name': 'Home',
                'id': 'None',
            }
        }
        assert_equal(expected, result)

    def test_format_project_wiki_pages(self):
        result = views.format_project_wiki_pages(node=self.project, auth=self.auth)
        expected = [
            {
                'page': {
                    'url': self.project.web_url_for('project_wiki_view', wname='home', _guid=True),
                    'name': 'Home',
                    'id': self.home_wiki._primary_key,
                }
            },
            {
                'page': {
                    'url': self.wiki_page1.url,
                    'name': self.wiki_page1.page_name,
                    'id': self.wiki_page1._id,
                    'sort_order': self.wiki_page1.sort_order
                },
                'children': []
            },
            {
                'page': {
                    'url': self.wiki_page2.url,
                    'name': self.wiki_page2.page_name,
                    'id': self.wiki_page2._id,
                    'sort_order': self.wiki_page1.sort_order
                },
                'children': [
                    {
                        'page': {
                            'url': self.wiki_child_page1.url,
                            'name': self.wiki_child_page1.page_name,
                            'id': self.wiki_child_page1._id,
                            'sort_order': self.wiki_child_page1.sort_order
                        },
                        'children': []
                    },
                    {
                        'page': {
                            'url': self.wiki_child_page2.url,
                            'name': self.wiki_child_page2.page_name,
                            'id': self.wiki_child_page2._id,
                            'sort_order': self.wiki_child_page2.sort_order
                        },
                        'children': []
                    },
                    {
                        'page': {
                            'url': self.wiki_child_page3.url,
                            'name': self.wiki_child_page3.page_name,
                            'id': self.wiki_child_page3._id,
                            'sort_order': self.wiki_child_page3.sort_order
                        },
                        'children': []
                    },
                ],
                'kind': 'folder'
            }
        ]
        assert_equal(expected, result)

    def test_format_child_wiki_pages(self):
        self.parent_wiki_page = WikiPage.objects.create_for_node(self.project, 'parentpage', 'parent content', self.consolidate_auth)
        self.child_wiki_page = WikiPage.objects.create_for_node(self.project, 'childpage', 'child content', self.consolidate_auth, self.parent_wiki_page)
        self.grandchild_wiki_page = WikiPage.objects.create_for_node(self.project, 'grandchild page', 'grandchild content', self.consolidate_auth, self.child_wiki_page)
        result = views.format_project_wiki_pages(node=self.project, auth=self.consolidate_auth)
        expected = [
            {
                'page': {
                    'url': self.project.web_url_for('project_wiki_view', wname='home', _guid=True),
                    'name': 'Home',
                    'id': self.home_wiki._primary_key,
                }
            },
            {
                'page': {
                    'url': self.wiki_page1.url,
                    'name': self.wiki_page1.page_name,
                    'id': self.wiki_page1._id,
                    'sort_order': self.wiki_page1.sort_order
                },
                'children': []
            },
            {
                'page': {
                    'url': self.wiki_page2.url,
                    'name': self.wiki_page2.page_name,
                    'id': self.wiki_page2._id,
                    'sort_order': self.wiki_page1.sort_order
                },
                'children': [
                    {
                        'page': {
                            'url': self.wiki_child_page1.url,
                            'name': self.wiki_child_page1.page_name,
                            'id': self.wiki_child_page1._id,
                            'sort_order': self.wiki_child_page1.sort_order
                        }
                    },
                    {
                        'page': {
                            'url': self.wiki_child_page2.url,
                            'name': self.wiki_child_page2.page_name,
                            'id': self.wiki_child_page2._id,
                            'sort_order': self.wiki_child_page2.sort_order
                        }
                    },
                    {
                        'page': {
                            'url': self.wiki_child_page3.url,
                            'name': self.wiki_child_page3.page_name,
                            'id': self.wiki_child_page3._id,
                            'sort_order': self.wiki_child_page3.sort_order
                        }
                    },
                ],
                'kind': 'folder'
            },
            {
                'page': {
                    'url': self.parent_wiki_page.url,
                    'name': self.parent_wiki_page.page_name,
                    'id': self.parent_wiki_page._id,
                    'sort_order': self.parent_wiki_page.sort_order
                },
                'children': [
                    {
                        'page': {
                            'url': self.child_wiki_page.url,
                            'name': self.child_wiki_page.page_name,
                            'id': self.child_wiki_page._id,
                            'sort_order': self.child_wiki_page.sort_order
                            },
                        'children': [
                            {
                                'page': {
                                    'url': self.grandchild_wiki_page.url,
                                    'name': self.grandchild_wiki_page.page_name,
                                    'id': self.grandchild_wiki_page._id,
                                    'sort_order': self.grandchild_wiki_page.sort_order
                                }
                            },
                        ],
                        'kind': 'folder'
                    },
                ],
                'kind': 'folder'
            },
        ]
        assert_equal(expected, result)

    def test_serialize_component_wiki(self):
        home_page = WikiPage.objects.create_for_node(self.component, 'home', 'content here', self.consolidate_auth)
        zoo_page = WikiPage.objects.create_for_node(self.component, 'zoo', 'koala', self.consolidate_auth)
        expected = [
            {
                'page': {
                    'name': self.component.title,
                    'url': self.component.web_url_for('project_wiki_view', wname='home', _guid=True),
                },
                'children': [
                    {
                        'page': {
                            'url': self.component.web_url_for('project_wiki_view', wname='home', _guid=True),
                            'name': 'Home',
                            'id': self.component._primary_key,
                        },
                    },
                    {
                        'page': {
                            'url': self.component.web_url_for('project_wiki_view', wname='zoo', _guid=True),
                            'name': 'zoo',
                            'sort_order': None,
                            'id': zoo_page._primary_key,
                        },
                        'children': [],
                    }
                ],
                'kind': 'component',
                'category': self.component.category,
                'pointer': False,
            }
        ]
        data = views.format_component_wiki_pages(node=self.project, auth=self.consolidate_auth)
        assert_equal(data, expected)

    @mock.patch('addons.wiki.utils.check_file_object_in_node')
    def test_project_wiki_validate_for_import(self, mock_check_file_object_in_node):
        mock_check_file_object_in_node.return_value = True
        dir_id = self.root_import_folder1._id
        url = self.project.api_url_for('project_wiki_validate_for_import', dir_id=dir_id)
        res = self.app.get(url)
        response_json = res.json
        task_id = response_json['taskId']
        uuid_obj = uuid.UUID(task_id)
        assert uuid_obj

    def test_project_wiki_validate_for_import_process(self):
        result = views.project_wiki_validate_for_import_process(
            self.root_import_folder_validate._id,
            self.project)
        assert_equal(result['duplicated_folder'], [])
        assert_true(result['canStartImport'])
        assert_count_equal(result['data'], [{'parent_wiki_name': 'importpage1', 'path': '/importpage1/importpage2', 'original_name': 'importpage2', 'wiki_name': 'importpage2', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_2._id}, {'parent_wiki_name': None, 'path': '/importpage1', 'original_name': 'importpage1', 'wiki_name': 'importpage1', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_1._id}])

    def test_validate_import_folder_invalid(self):
        folder = BaseFileNode.objects.get(name='importpagex', target_object_id=self.project.id).first()
        parent_path = ''
        result = views._validate_import_folder(self.project, folder, parent_path)
        for info in result:
            assert_equal(info['path'], '/importpagex')
            assert_equal(info['original_name'], 'importpagex')
            assert_equal(info['name'], 'importpagex')
            assert_equal(info['status'], 'invalid')
            assert_equal(info['message'], 'The wiki page does not exist, so the subordinate pages are not processed.')

    def test_validate_import_folder(self):
        folder = self.import_page_folder_1
        parent_path = ''
        result = views._validate_import_folder(self.project, folder, parent_path)
        expected_results = [
            {'parent_wiki_name': 'importpage1', 'path': '/importpage1/importpage2', 'original_name': 'importpage2', 'wiki_name': 'importpage2', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_2._id},
            {'parent_wiki_name': None, 'path': '/importpage1', 'original_name': 'importpage1', 'wiki_name': 'importpage1', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_1._id}
        ]
        for expected_result in expected_results:
            assert_in(expected_result, result)

    def test_validate_import_wiki_exists_duplicated_valid_exists_status_change(self):
        info = {'wiki_name': 'importpagea', 'path': '/importpagea', 'status': 'valid'}
        result, can_start_import = views._validate_import_wiki_exists_duplicated(self.project, info)
        assert_equal(result['status'], 'valid_exists')
        assert_false(can_start_import)

    def test_validate_import_wiki_exists_duplicated_valid_duplicated_status_change(self):
        info = {'wiki_name': 'importpageb', 'path': '/importpagea/importpageb', 'status': 'valid'}
        result, can_start_import = views._validate_import_wiki_exists_duplicated(self.project, info)
        assert_equal(result['status'], 'valid_duplicated')
        assert_false(can_start_import)

    def test_validate_import_duplicated_directry_no_duplicated(self):
        info_list = []
        result = views._validate_import_duplicated_directry(info_list)
        assert_equal(result, [])

    def test_validate_import_duplicated_directry_duplicated(self):
        info_list = [
            {'original_name': 'folder1'},
            {'original_name': 'folder2'},
            {'original_name': 'folder1'},
            {'original_name': 'folder3'}
        ]
        result = views._validate_import_duplicated_directry(info_list)
        assert_equal(result, ['folder1'])

    @mock.patch('addons.wiki.views.project_wiki_import_process')
    @mock.patch('addons.wiki.utils.check_file_object_in_node')
    def test_project_wiki_import(self, mock_check_file_object_in_node, mock_project_wiki_import_process):
        mock_check_file_object_in_node.return_value = True
        dir_id = self.root_import_folder1._id
        url = self.project.api_url_for('project_wiki_import', dir_id=dir_id)
        res = self.app.post_json(url, { 'data': [{'test': 'test1'}] }, auth=self.user.auth)
        response_json = res.json
        task_id = response_json['taskId']
        uuid_obj = uuid.UUID(task_id)
        assert_is_not_none(uuid_obj)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    @mock.patch('addons.wiki.views._wiki_import_create_or_update')
    @mock.patch('addons.wiki.views._import_same_level_wiki')
    @mock.patch('addons.wiki.tasks.run_update_search_and_bulk_index')
    def test_project_wiki_import_process(self, mock_run_task_elasticsearch, mock_import_same_level_wiki, mock_wiki_import_create_or_update, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        # root
        # └── rootimportfolder2
        #     ├── importpage1
        #     │   ├── importpage1.md
        #     │   └── importpage2
        #     │       ├── importpage2.md
        #     │       └── importpage3
        #     │           └── importpage3.md
        #     └── importpage4
        #         ├── importpage4.md
        #         └── importpage5
        #             └── importpage5.md
        self.root_import_folder = TestFolderWiki.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        self.import_page_folder_1 = TestFolderWiki.objects.create(name='importpage1', target=self.project, parent=self.root_import_folder)
        self.import_page_md_file_1 = TestFileWiki.objects.create(name='importpage1.md', target=self.project, parent=self.import_page_folder_1)
        self.import_page_folder_2 = TestFolderWiki.objects.create(name='importpage2', target=self.project, parent=self.import_page_folder_1)
        self.import_page_md_file_2 = TestFileWiki.objects.create(name='importpage2.md', target=self.project, parent=self.import_page_folder_2)
        self.import_page_folder_3 = TestFolderWiki.objects.create(name='importpage3', target=self.project, parent=self.import_page_folder_2)
        self.import_page_md_file_3 = TestFileWiki.objects.create(name='importpage3.md', target=self.project, parent=self.import_page_folder_3)
        self.import_page_folder_4 = TestFolderWiki.objects.create(name='importpage4', target=self.project, parent=self.root_import_folder)
        self.import_page_md_file_4 = TestFileWiki.objects.create(name='importpage4.md', target=self.project, parent=self.import_page_folder_4)
        self.import_page_folder_5 = TestFolderWiki.objects.create(name='importpage5', target=self.project, parent=self.import_page_folder_4)
        self.import_page_md_file_5 = TestFileWiki.objects.create(name='importpage5.md', target=self.project, parent=self.import_page_folder_5)
        mock_get_md_content_from_wb.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_get_or_create_wiki_folder.side_effect = [(123, 'osfstorage/wikiimage_id/'), (456, 'osfstorage/wikiimportedfolder_id/')]
        mock_create_wiki_folder.return_value = 789, 'osfstorage/wikisortedcopyfolder_id/'
        mock_wiki_copy_import_directory.return_value = 'clone_id'
        mock_wiki_content_replace.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_wiki_import_create_or_update.side_effect = [({'status': 'success', 'path': '/importpage4'}, 4), ({'status': 'success', 'path': '/importpage1'}, 1)]
        mock_import_same_level_wiki.side_effect = [([{'status': 'success', 'path': '/importpage4/importpage5'}, {'status': 'success', 'path': '/importpage1/importpage2'}], [5, 2]), ([{'status': 'success', 'path': '/importpage1/importpage2/importpage3'}], [3])]

        expected_result = {
            'ret': [
                {'status': 'success', 'path': '/importpage4'},
                {'status': 'success', 'path': '/importpage1'},
                {'status': 'success', 'path': '/importpage4/importpage5'},
                {'status': 'success', 'path': '/importpage1/importpage2'},
                {'status': 'success', 'path': '/importpage1/importpage2/importpage3'}
            ],
            'import_errors': []
        }

        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        assert_equal(result, expected_result)
        mock_run_task_elasticsearch.delay.assert_called_once_with(self.project.guids.first()._id, [4, 1, 5, 2, 3])
        task = WikiImportTask.objects.get(task_id='task_id')
        assert_equal(task.status, task.STATUS_COMPLETED)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    @mock.patch('addons.wiki.views._wiki_import_create_or_update')
    @mock.patch('addons.wiki.tasks.run_update_search_and_bulk_index')
    @mock.patch('addons.wiki.views.set_wiki_import_task_proces_end')
    def test_project_wiki_import_process_top_level_aborted(self, mock_wiki_import_task_prcess_end, mock_run_task_elasticsearch, mock_wiki_import_create_or_update, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolderWiki.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        mock_get_md_content_from_wb.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_get_or_create_wiki_folder.side_effect = [(123, 'osfstorage/wikiimage_id/'), (456, 'osfstorage/wikiimportedfolder_id/')]
        mock_create_wiki_folder.return_value = 789, 'osfstorage/wikisortedcopyfolder_id/'
        mock_wiki_copy_import_directory.return_value = 'clone_id'
        mock_wiki_content_replace.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_wiki_import_create_or_update.side_effect = views.ImportTaskAbortedError

        expected_result = {'aborted': True}

        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        assert_equal(result, expected_result)
        mock_run_task_elasticsearch.delay.assert_called_once_with(self.project.guids.first()._id, [])
        mock_wiki_import_task_prcess_end.assert_called_once_with(self.project)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    @mock.patch('addons.wiki.views._wiki_import_create_or_update')
    @mock.patch('addons.wiki.views._import_same_level_wiki')
    @mock.patch('addons.wiki.tasks.run_update_search_and_bulk_index')
    @mock.patch('addons.wiki.views.set_wiki_import_task_proces_end')
    def test_project_wiki_import_process_sub_level_aborted(self, mock_wiki_import_task_prcess_end, mock_run_task_elasticsearch, mock_import_same_level_wiki, mock_wiki_import_create_or_update, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolderWiki.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        mock_get_md_content_from_wb.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_get_or_create_wiki_folder.side_effect = [(123, 'osfstorage/wikiimage_id/'), (456, 'osfstorage/wikiimportedfolder_id/')]
        mock_create_wiki_folder.return_value = 789, 'osfstorage/wikisortedcopyfolder_id/'
        mock_wiki_copy_import_directory.return_value = 'clone_id'
        mock_wiki_content_replace.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_wiki_import_create_or_update.side_effect = [({'status': 'success', 'path': '/importpage4'}, 4), ({'status': 'success', 'path': '/importpage1'}, 1)]
        mock_import_same_level_wiki.side_effect = ImportTaskAbortedError

        expected_result = {'aborted': True}

        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        assert_equal(result, expected_result)
        mock_run_task_elasticsearch.delay.assert_called_once_with(self.project.guids.first()._id, [4, 1])
        mock_wiki_import_task_prcess_end.assert_called_once_with(self.project)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    def test_project_wiki_import_process_wb_aborted(self, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolderWiki.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        mock_get_md_content_from_wb.return_value = None
        expected_result = {'aborted': True}
        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        assert_equal(result, expected_result)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    def test_project_wiki_import_process_replace_aborted(self, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolderWiki.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        self.root_import_folder = TestFolderWiki.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        mock_get_md_content_from_wb.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_get_or_create_wiki_folder.side_effect = [(123, 'osfstorage/wikiimage_id/'), (456, 'osfstorage/wikiimportedfolder_id/')]
        mock_create_wiki_folder.return_value = 789, 'osfstorage/wikisortedcopyfolder_id/'
        mock_wiki_copy_import_directory.return_value = 'clone_id'
        mock_wiki_content_replace.return_value = None
        expected_result = {'aborted': True}
        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        assert_equal(result, expected_result)

    def test_replace_wiki_link_notation_wiki_page_with_tooptip(self):
        wiki_page1_sp = WikiPage.objects.create_for_node(self.project, 'wiki page1', 'wiki pagea content', self.consolidate_auth)
        wiki_content_link = 'Wiki content with [wiki page1](wiki%20page1 \"tooltip1\")'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link))
        info = self.wiki_info
        expected_content = f'Wiki content with [wiki page1](../wiki%20page1/ \"tooltip1\")'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link, info, self.node_file_mapping, self.import_wiki_name_list, self.root_import_folder1._id)
        assert_equal(result_content, expected_content)

    def test_replace_wiki_link_notation_wiki_page_without_tooptip(self):
        wiki_page1_sp = WikiPage.objects.create_for_node(self.project, 'wiki page1', 'wiki pagea content', self.consolidate_auth)
        wiki_content_link = 'Wiki content with [wiki page1](wiki%20page1)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link))
        info = self.wiki_info
        expected_content = f'Wiki content with [wiki page1](../wiki%20page1/)'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link, info, self.node_file_mapping, self.import_wiki_name_list, self.root_import_folder1._id)
        assert_equal(result_content, expected_content)

    def test_replace_wiki_link_notation_attachment_file(self):
        wiki_content_link_attachment = 'Wiki content with [attachment1.doc](attachment1.doc)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_attachment))
        info = self.wiki_info
        expected_content = f'Wiki content with [attachment1.doc]({website_settings.DOMAIN}{self.guid}/files/osfstorage/{self.import_attachment1_doc._id})'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_attachment, info, self.node_file_mapping, self.import_wiki_name_list, self.root_import_folder1._id)
        assert_equal(result_content, expected_content)

    def test_replace_wiki_link_notation_has_slash(self):
        wiki_content_link_has_slash = 'Wiki content with [wiki/page](wiki/page)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_has_slash))
        info = self.wiki_info
        expected_content = wiki_content_link_has_slash
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_has_slash, info, self.node_file_mapping, self.import_wiki_name_list, self.root_import_folder1._id)
        assert_equal(result_content, expected_content)

    def test_replace_wiki_link_notation_has_sharp_and_is_wiki_with_tooltip(self):
        wiki_content_link = 'Wiki content with [importpage1#anchor](importpage1#anchor \"tooltip text\")'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link))
        info = self.wiki_info
        expected_content = 'Wiki content with [importpage1#anchor](../importpage1/#anchor \"tooltip text\")'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link, info, self.node_file_mapping, self.import_wiki_name_list, self.root_import_folder1._id)
        assert_equal(result_content, expected_content)

    def test_replace_wiki_link_notation_has_sharp_and_is_wiki_without_tooltip(self):
        wiki_content_link = 'Wiki content with [importpage1#anchor](importpage1#anchor)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link))
        info = self.wiki_info
        expected_content = 'Wiki content with [importpage1#anchor](../importpage1/#anchor)'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link, info, self.node_file_mapping, self.import_wiki_name_list, self.root_import_folder1._id)
        assert_equal(result_content, expected_content)

    def test_replace_wiki_link_notation_is_url(self):
        wiki_content_link_is_url = 'Wiki content with [example](https://example.com)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_is_url))
        info = self.wiki_info
        expected_content = wiki_content_link_is_url
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_is_url, info, self.node_file_mapping, self.import_wiki_name_list, self.root_import_folder1._id)
        assert_equal(result_content, expected_content)

    def test_replace_wiki_link_notation_no_link(self):
        wiki_content = 'Wiki content'
        link_matches = list(re.finditer(self.rep_link, wiki_content))
        info = self.wiki_info
        expected_content = wiki_content
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content, info, self.node_file_mapping, self.import_wiki_name_list, self.root_import_folder1._id)
        assert_equal(result_content, expected_content)

    def test_check_wiki_name_exist(self):
        exist_wiki_name1 = 'exist1'
        exist_wiki_name2 = 'exist2'
        exist_wiki_name_uni = 'existが'
        exist_wiki_name_uni_nfc = unicodedata.normalize('NFC', exist_wiki_name_uni)
        exist_wiki_name_uni_nfd = unicodedata.normalize('NFD', exist_wiki_name_uni)
        WikiPage.objects.create_for_node(self.project, exist_wiki_name1, 'wiki page exist1 content', self.consolidate_auth)
        WikiPage.objects.create_for_node(self.project, exist_wiki_name2, 'wiki page exist2 content', self.consolidate_auth)
        WikiPage.objects.create_for_node(self.project, exist_wiki_name_uni, 'wiki page exist3 content', self.consolidate_auth)

        import_wiki_name1 = 'importpage1'
        import_wiki_name2 = 'importpage2'
        import_wiki_name_uni = 'importpageが'
        import_wiki_name_uni_nfc = unicodedata.normalize('NFC', self.import_wiki_name_uni)
        import_wiki_name_uni_nfd = unicodedata.normalize('NFD', self.import_wiki_name_uni)
        import_wiki_name_list = [import_wiki_name1, import_wiki_name2, import_wiki_name_uni]

        dobuled_names = [exist_wiki_name1, exist_wiki_name2, exist_wiki_name_uni,
            exist_wiki_name_uni_nfc, exist_wiki_name_uni_nfd,
            import_wiki_name1, import_wiki_name2, import_wiki_name_uni,
            import_wiki_name_uni_nfc, import_wiki_name_uni_nfd]
        new_names = ['new_page1', 'new_page2', 'new_pageが']

        # dubled names
        for wiki_name in dobuled_names:
          result = views._check_wiki_name_exist(self.project, wiki_name, self.node_file_mapping, import_wiki_name_list)
          assert_true(result)

        # new names
        for wiki_name in new_names:
          result = views._check_wiki_name_exist(self.project, wiki_name, self.node_file_mapping, import_wiki_name_list)
          assert_false(result)

    def test_replace_file_name_image_with_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png \"tooltip1\")'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with ![](<{website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render> \"tooltip1\")'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        assert_equal(result, expected_content)

    def test_replace_file_name_image_without_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render)'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        assert_equal(result, expected_content)

    def test_replace_file_name_image_with_size_with_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png \"tooltip2\" =200)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with ![](<{website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render =200> \"tooltip2\")'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        assert_equal(result, expected_content)

    def test_replace_file_name_image_with_size_without_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png =200)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render =200)'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        assert_equal(result, expected_content)

    def test_replace_file_name_image_with_invalid_size_with_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png \"tooltip\" =abcde)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = wiki_content_image_tooltip
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        assert_equal(result, expected_content)

    def test_replace_file_name_image_with_invalid_size_without_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png =abcde)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = wiki_content_image_tooltip
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        assert_equal(result, expected_content)

    def test_replace_file_name_link_with_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_link_tooltip = 'Wiki content with [attachment1.doc](attachment1.doc \"tooltip1\")'
        match = list(re.finditer(self.rep_link, wiki_content_link_tooltip))[0]
        notation = 'link'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with [attachment1.doc]({website_settings.DOMAIN}{self.guid}/files/osfstorage/{self.import_attachment1_doc._id} \"tooltip1\")'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_link_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        assert_equal(result, expected_content)

    def test_replace_file_name_link_without_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_link_tooltip = 'Wiki content with [attachment1.doc](attachment1.doc)'
        match = list(re.finditer(self.rep_link, wiki_content_link_tooltip))[0]
        notation = 'link'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with [attachment1.doc]({website_settings.DOMAIN}{self.guid}/files/osfstorage/{self.import_attachment1_doc._id})'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_link_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        assert_equal(result, expected_content)

    def test_filename(self):
        match_path = 'test.png'
        expected_path = 'test.png'
        file_name, image_size = views._split_image_and_size(match_path)
        assert_equal(file_name, expected_path)
        assert_equal(image_size, '')

    def test_filename_size(self):
        match_path = 'test.png =200'
        expected_path = 'test.png'
        file_name, image_size = views._split_image_and_size(match_path)
        assert_equal(file_name, expected_path)
        assert_equal(image_size, ' =200')

    def test_filename_invalid_size(self):
        match_path = 'test.png =abcde'
        expected_path = match_path
        file_name, image_size = views._split_image_and_size(match_path)
        assert_equal(file_name, expected_path)
        assert_equal(image_size, '')

    def test_has_slash(self):
        path = 'meeting 4/24'
        result = views._exclude_symbols(path)
        assert_true(result[0])
        assert_false(result[1])
        assert_false(result[2])

    def test_is_url(self):
        path = 'https://example.com'
        result = views._exclude_symbols(path)
        assert_true(result[0])
        assert_false(result[1])
        assert_true(result[2])

    def test_has_sharp(self):
        path = 'wiki#anchor'
        result = views._exclude_symbols(path)
        assert_false(result[0])
        assert_true(result[1])
        assert_false(result[2])

    def test_no_tooltip(self):
        match_path = 'test.txt'
        expected_path = 'test.txt'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        assert_equal(result_path, expected_path)
        assert_is_none(result_tooptip)

    def test_single_quote_tooltip(self):
        match_path = 'test.txt \'tooltip\''
        expected_path = 'test.txt'
        expected_tooltip = 'tooltip'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        assert_equal(result_path, expected_path)
        assert_equal(result_tooptip['tooltip'], expected_tooltip)

    def test_double_quote_tooltip(self):
        match_path = 'test.txt \"tooltip\"'
        expected_path = 'test.txt'
        expected_tooltip = 'tooltip'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        assert_equal(result_path, expected_path)
        assert_equal(result_tooptip['tooltip'], expected_tooltip)

    def test_backslash_in_tooltip(self):
        match_path = r'test.txt "to\\\\ol\"\\tip"'
        expected_path = 'test.txt'
        expected_tooltip = 'to\\\\\\\\ol\\"\\\\tip'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        assert_equal(result_path, expected_path)
        assert_equal(result_tooptip['tooltip'], expected_tooltip)

    def test_empty_tooltip(self):
        match_path = 'test.txt \"\"'
        expected_path = 'test.txt'
        expected_tooltip = ''
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        assert_equal(result_path, expected_path)
        assert_equal(result_tooptip['tooltip'], expected_tooltip)

    def test_single_quote_tooltip_size(self):
        match_path = 'test.png \'tooltip\' =200'
        expected_path = 'test.png =200'
        expected_tooltip = 'tooltip'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        assert_equal(result_path, expected_path)
        assert_equal(result_tooptip['tooltip'], expected_tooltip)

    def test_double_quote_tooltip_size(self):
        match_path = 'test.png \"tooltip\" =200'
        expected_path = 'test.png =200'
        expected_tooltip = 'tooltip'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        assert_equal(result_path, expected_path)
        assert_equal(result_tooptip['tooltip'], expected_tooltip)

    def test_no_tooltip_with_size(self):
        match_path = 'test.png =200'
        expected_path = 'test.png =200'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        assert_equal(result_path, expected_path)
        assert_is_none(result_tooptip)

    def test_check_attachment_file_name_exist_has_hat(self):
        wiki_name = 'importpage1'
        file_name = 'importpage2^attachment3.xlsx'
        result_id = views._check_attachment_file_name_exist(wiki_name, file_name, self.root_import_folder1._id, self.node_file_mapping)
        assert_equal(result_id, self.import_attachment3_xlsx._id)

    def test_check_attachment_file_name_exist_has_not_hat(self):
        wiki_name = 'importpage1'
        file_name = 'attachment1.doc'
        result_id = views._check_attachment_file_name_exist(wiki_name, file_name, self.root_import_folder1._id, self.node_file_mapping)
        assert_equal(result_id, self.import_attachment1_doc._id)

    def test_process_attachment_file_name_exist(self):
        wiki_name = 'importpage1'
        file_name = 'attachment1.doc'
        result_id = views._process_attachment_file_name_exist(wiki_name, file_name, self.root_import_folder1._id, self.node_file_mapping)
        assert_equal(result_id, self.import_attachment1_doc._id)

    def test_process_attachment_file_name_exist_nfd(self):
        wiki_name = 'importpage1'
        file_name = 'attachment1.doc'
        wiki_name_nfd = unicodedata.normalize('NFD', wiki_name)
        file_name_nfd = unicodedata.normalize('NFD', file_name)
        result_id = views._process_attachment_file_name_exist(wiki_name_nfd, file_name_nfd, self.root_import_folder1._id, self.node_file_mapping)
        assert_equal(result_id, self.import_attachment1_doc._id)

    def test_process_attachment_file_name_exist_not_exist(self):
        wiki_name = 'importpage1'
        file_name = 'not_existing_file.doc'
        result_content = views._process_attachment_file_name_exist(wiki_name, file_name, self.root_import_folder1._id, self.node_file_mapping)
        assert_is_none(result_content)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_aborted(self, mock_task):
        mock_task.is_aborted.return_value = True
        expected_content = 'wiki paged content'
        with assert_raises(ImportTaskAbortedError):
            views._wiki_import_create_or_update('/importpagec/importpaged', 'wiki paged content', self.consolidate_auth ,self.project2, mock_task, 'importpagec')

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_update_not_changed(self, mock_task):
        mock_task.is_aborted.return_value = False
        expected_content = 'wiki paged content'
        result, updated_wiki_id = views._wiki_import_create_or_update('/importpagec/importpaged', 'wiki paged content', self.consolidate_auth ,self.project2, mock_task, 'importpagec')
        assert_equal(result, {'status': 'unmodified', 'path': '/importpagec/importpaged'})
        assert_is_none(updated_wiki_id)
        new_wiki_version = WikiVersion.objects.get_for_node(self.project2, 'importpaged')
        assert_equal(new_wiki_version.content, 'wiki paged content')

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_update_changed(self, mock_task):
        mock_task.is_aborted.return_value = False
        expected_content = 'new wiki paged content'
        result, updated_wiki_id = views._wiki_import_create_or_update('/importpagec/importpaged', 'new wiki paged content', self.consolidate_auth ,self.project2, mock_task, 'importpagec')
        assert_equal(result, {'status': 'success', 'path': '/importpagec/importpaged'})
        assert_equal(self.wiki_page4.id, updated_wiki_id)
        new_wiki_version = WikiVersion.objects.get_for_node(self.project2, 'importpaged')
        assert_equal(new_wiki_version.content, expected_content)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_create_home(self, mock_task):
        mock_task.is_aborted.return_value = False
        expected_content = 'home wiki page content'
        result, updated_wiki_id = views._wiki_import_create_or_update('/HOME', 'home wiki page content', self.consolidate_auth ,self.project2, mock_task)
        assert_equal(result, {'status': 'success', 'path': '/HOME'})
        new_wiki_version = WikiVersion.objects.get_for_node(self.project2, 'home')
        assert_equal(new_wiki_version.wiki_page.id, updated_wiki_id)
        assert_equal(new_wiki_version.content, expected_content)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_create(self, mock_task):
        mock_task.is_aborted.return_value = False
        expected_content = 'wiki page content'
        result, updated_wiki_id = views._wiki_import_create_or_update('/wikipagename', 'wiki page content', self.consolidate_auth ,self.project2, mock_task)
        assert_equal(result, {'status': 'success', 'path': '/wikipagename'})
        new_wiki_version = WikiVersion.objects.get_for_node(self.project2, 'wikipagename')
        assert_equal(new_wiki_version.wiki_page.id, updated_wiki_id)
        assert_equal(new_wiki_version.content, expected_content)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_update_changed_nfd(self, mock_task):
        mock_task.is_aborted.return_value = False
        path_nfd = unicodedata.normalize('NFD', '/importpagec/importpaged')
        content_nfd = unicodedata.normalize('NFD', 'new wiki paged content')
        parent_name_nfd = unicodedata.normalize('NFD', 'importpagec')
        expected_content = 'new wiki paged content'
        result, updated_wiki_id = views._wiki_import_create_or_update(path_nfd, content_nfd, self.consolidate_auth ,self.project2, mock_task, parent_name_nfd)
        assert_equal(result, {'status': 'success', 'path': '/importpagec/importpaged'})
        assert_equal(self.wiki_page4.id, updated_wiki_id)
        new_wiki_version = WikiVersion.objects.get_for_node(self.project2, 'importpaged')
        assert_equal(new_wiki_version.content, expected_content)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_does_not_exist_parent(self, mock_task):
        mock_task.is_aborted.return_value = False
        expected_content = 'wiki page content'
        with assert_raises(Exception) as cm:
            views._wiki_import_create_or_update('/wikipagename', 'wiki page content', self.consolidate_auth ,self.project2, mock_task, 'notexisitparentwiki')

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_content_replace_no_abort(self,mock_task):
        mock_task.is_aborted.return_value = False
        wiki_info = [
            {
                'parent_wiki_name': None,
                'path': '/page1',
                'original_name': 'page1',
                'wiki_name': 'page1',
                'status': 'valid',
                'message': '',
                '_id': 'xxx',
                'wiki_content': 'content1'
            },
            {
                'parent_wiki_name': None,
                'path': '/page2',
                'original_name': 'page2',
                'wiki_name': 'page2',
                'status': 'valid',
                'message': '',
                '_id': 'yyy',
                'wiki_content': 'content2'
            },
            {
                'parent_wiki_name': 'page2',
                'path': '/page2/page3',
                'original_name': 'page3',
                'wiki_name': 'page3',
                'status': 'valid',
                'message': '',
                '_id': 'zzz',
                'wiki_content': 'content3'
            }
        ]
        dir_id = self.root_import_folder1._id
        node=self.node
        replaced_wiki_info = views._wiki_content_replace(wiki_info,dir_id,node,mock_task)
        assert_equal(wiki_info, replaced_wiki_info)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_content_replace_aborted(self,mock_task):
        mock_task.is_aborted.return_value = True
        wiki_info = [
            {
                'parent_wiki_name': None,
                'path': '/page1',
                'original_name': 'page1',
                'wiki_name': 'page1',
                'status': 'valid',
                'message': '',
                '_id': 'xxx',
                'wiki_content': 'content1'
            },
            {
                'parent_wiki_name': None,
                'path': '/page2',
                'original_name': 'page2',
                'wiki_name': 'page2',
                'status': 'valid',
                'message': '',
                '_id': 'yyy',
                'wiki_content': 'content2'
            },
            {
                'parent_wiki_name': 'page2',
                'path': '/page2/page3',
                'original_name': 'page3',
                'wiki_name': 'page3',
                'status': 'valid',
                'message': '',
                '_id': 'zzz',
                'wiki_content': 'content3'
            }
        ]
        dir_id = self.root_import_folder1._id
        node=self.node
        replaced_wiki_info = views._wiki_content_replace(wiki_info,dir_id,node,mock_task)
        assert_equal(replaced_wiki_info, None)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_content_replace_missing_content(self,mock_task):
        mock_task.is_aborted.return_value = False
        wiki_info_input_date = [
            {
                'parent_wiki_name': None,
                'path': '/page1',
                'original_name': 'page1',
                'wiki_name': 'page1',
                'status': 'valid',
                'message': '',
                '_id': 'xxx',
                'wiki_content': 'content1'
            },
            {
                'parent_wiki_name': None,
                'path': '/page2',
                'original_name': 'page2',
                'wiki_name': 'page2',
                'status': 'valid',
                'message': '',
                '_id': 'yyy'
            },
            {
                'parent_wiki_name': 'page2',
                'path': '/page2/page3',
                'original_name': 'page3',
                'wiki_name': 'page3',
                'status': 'valid',
                'message': '',
                '_id': 'zzz',
                'wiki_content': 'content3'
            }
        ]

        wiki_info_output_date = [
            {
                'parent_wiki_name': None,
                'path': '/page1',
                'original_name': 'page1',
                'wiki_name': 'page1',
                'status': 'valid',
                'message': '',
                '_id': 'xxx',
                'wiki_content': 'content1'
            },
            {
                'parent_wiki_name': 'page2',
                'path': '/page2/page3',
                'original_name': 'page3',
                'wiki_name': 'page3',
                'status': 'valid',
                'message': '',
                '_id': 'zzz',
                'wiki_content': 'content3'
            }
        ]
        dir_id = self.root_import_folder1._id
        node=self.node
        replaced_wiki_info = views._wiki_content_replace(wiki_info_input_date, dir_id, node, mock_task)
        assert_equal(wiki_info_output_date, replaced_wiki_info)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_import_same_level_wiki_task_aborted(self,mock_task):
        mock_task.is_aborted.return_value = True
        wiki_info = [
            {
                'parent_wiki_name': None,
                'path': '/importpagec',
                'original_name': self.wiki_page3.page_name,
                'wiki_name': self.wiki_page3.page_name,
                'status': 'valid',
                'message': '',
                '_id': self.wiki_page3._id,
                'wiki_content': 'updated content'
            }
        ]
        with assert_raises(ImportTaskAbortedError):
            views._import_same_level_wiki(wiki_info, 0, self.consolidate_auth, self.project2, mock_task)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_import_same_level_wiki_matching_depth(self, mock_task):
        mock_task.is_aborted.return_value = False
        wiki_info = [
            {
                'parent_wiki_name': None,
                'path': '/importpagec',
                'original_name': self.wiki_page3.page_name,
                'wiki_name': self.wiki_page3.page_name,
                'status': 'valid',
                'message': '',
                '_id': self.wiki_page3._id,
                'wiki_content': 'updated content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpagee',
                'original_name': 'new_pagea',
                'wiki_name': 'new_pagea',
                'status': 'valid',
                'message': '',
                '_id': None,
                'wiki_content': 'new content'
            },
        ]
        expected_ret = [
            {'status': 'success', 'path': '/importpagec'},
            {'status': 'success', 'path': '/importpagee'},
        ]
        ret, wiki_id_list = views._import_same_level_wiki(wiki_info, 0, self.consolidate_auth2, self.project2, mock_task)
        assert_equal(expected_ret, ret)
        assert_equal(self.wiki_page3.id, wiki_id_list[0])
        assert_is_not_none(wiki_id_list[1])

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_import_same_level_wiki_unmatched_depth(self, mock_task):
        mock_task.is_aborted.return_value = False
        wiki_info = [
            {
                'parent_wiki_name': None,
                'path': '/importpagec',
                'original_name': self.wiki_page3.page_name,
                'wiki_name': self.wiki_page3.page_name,
                'status': 'valid',
                'message': '',
                '_id': self.wiki_page3._id,
                'wiki_content': 'updated content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpagee',
                'original_name': 'new_pagea',
                'wiki_name': 'new_pagea',
                'status': 'valid',
                'message': '',
                '_id': None,
                'wiki_content': 'new content'
            },
        ]
        expected_ret = []
        expectec_ids = []
        ret, wiki_id_list = views._import_same_level_wiki(wiki_info, 2, self.consolidate_auth2, self.project2, mock_task)
        assert_equal(expected_ret, ret)
        assert_equal([], wiki_id_list)

    @mock.patch('addons.wiki.views.AsyncResult')
    def project_get_task_result_not_ready(self, mock_async_result):
        mock_res = MagicMock()
        mock_res.ready.return_value = False
        mock_async_result.return_value = mock_res
        node = MagicMock()
        result = views.project_get_task_result('task_id',node)
        assert_is_none(result)

    @mock.patch('addons.wiki.views.AsyncResult')
    def project_get_task_result_not_ready(self, mock_async_result):
        mock_res = MagicMock()
        mock_async_result.return_value = mock_res
        mock_res.ready.return_value = True
        mock_res.get.return_value = 'expected_result'
        node = MagicMock()
        result = views.project_get_task_result('task_id',node)
        assert_equal(result,'expected_result')

    @mock.patch('addons.wiki.views.AsyncResult')
    @mock.patch('addons.wiki.views._extract_err_msg')
    def project_get_task_result_not_ready(self,mock_err_msg, mock_async_result):
        mock_res = MagicMock()
        mock_res.ready.return_value = True
        mock_res.get.side_effect = Exception('exception')
        mock_async_result.return_value = mock_res
        mock_err_msg.return_value = 'error500'
        node = MagicMock()
        with assert_raises(HTTPError) as context:
            views.project_get_task_result('task_id',node)
        assert_equal(context.exception.data['message_long'], 'error500')

    def test_replace_wiki_image_two_image_matches(self):
        wiki_content_two_image = 'Wiki content with ![](image1.png) and ![](image2.png)'
        self.two_image_matches = list(re.finditer(self.rep_image, wiki_content_two_image))
        expected_content = f'Wiki content with ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render) and ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image2._id}?mode=render)'
        wiki_content = views._replace_wiki_image(self.project, self.two_image_matches, wiki_content_two_image, self.wiki_info, self.root_import_folder1._id, self.node_file_mapping)
        assert_equal(wiki_content, expected_content)

    def test_replace_wiki_image_match_with_slash(self):
        wiki_content_image_with_slash = 'Wiki content with ![](ima/ge3.png)'
        self.slash_image_matches = list(re.finditer(self.rep_image, wiki_content_image_with_slash))
        expected_content = wiki_content_image_with_slash = 'Wiki content with ![](ima/ge3.png)'
        wiki_content = views._replace_wiki_image(self.project, self.slash_image_matches, wiki_content_image_with_slash, self.wiki_info, self.root_import_folder1._id, self.node_file_mapping)
        assert_equal(wiki_content, expected_content)

    def test_url_decoding(self):
        input_name = 'my%20example%20file.txt'
        expected_output = 'my example file.txt'
        actual_output = views._replace_common_rule(input_name)
        assert_equal(actual_output, expected_output)

    def test_mixed_url_decoding(self):
        input_name = 'another%2Bexample%2Bfile.txt'
        expected_output = 'another+example+file.txt'
        actual_output = views._replace_common_rule(input_name)
        assert_equal(actual_output, expected_output)

    @mock.patch('addons.wiki.views.BaseFileNode')
    def test_get_or_create_wiki_folder_get(self, mock_base_file_node):
        mock_base_file_node_instance = mock.Mock()
        mock_base_file_node_instance.id = 1
        mock_base_file_node_instance._id = 'aabbcc'
        mock_base_file_node.objects.get.return_value = mock_base_file_node_instance
        osf_cookie = self.osf_cookie
        creator, creator_auth = get_creator_auth_header(self.user)
        p_guid = self.guid
        folder_id, folder_path = views._get_or_create_wiki_folder(osf_cookie, self.project, self.root.id, self.user, creator_auth, 'Wiki images', parent_path='osfstorage/')
        assert_equal(folder_id, 1)
        assert_equal(folder_path, 'osfstorage/aabbcc/')

    @mock.patch('addons.wiki.views._create_wiki_folder')
    def test_get_or_create_wiki_folder_create(self, mock_create_wiki_folder):
        mock_create_wiki_folder.return_value = (1, 'osfstorage/xxyyzz/')
        osf_cookie = self.osf_cookie
        creator, creator_auth = get_creator_auth_header(self.user)
        p_guid = self.guid
        folder_id, folder_path = views._get_or_create_wiki_folder(osf_cookie, self.project, self.root.id, self.user, creator_auth, 'Wiki images', parent_path='osfstorage/')
        assert_equal(folder_id, 1)
        assert_equal(folder_path, 'osfstorage/xxyyzz/')

    @mock.patch('website.util.waterbutler.create_folder')
    def test_create_wiki_folder_success(self, mock_create_folder):
        mock_response = {
            'data': {
                'id': 'osfstorage/xxyyzz/',
                'attributes': {
                    'path': '/xxyyzz/'
                }
            }
        }
        mock_create_folder.return_value = MockResponse(mock_response, 200)

        def mock_create_folder_side_effect(osf_cookie, pid, folder_name, dest_path):
            TestFolderWiki.objects.create(
                name=folder_name,
                target=self.project,
                _path=dest_path,
                _id='xxyyzz'
            )
            return MockResponse(mock_response, 200)
        mock_create_folder.side_effect = mock_create_folder_side_effect

        osf_cookie = self.osf_cookie
        p_guid = self.guid
        folder_name = 'Wiki images'
        parent_path = 'osfstorage/'
        folder_id, folder_path = views._create_wiki_folder(osf_cookie, p_guid, folder_name, parent_path)

        expected_folder_path = 'osfstorage/xxyyzz/'

        assert_equal(folder_path, expected_folder_path)

    @mock.patch('website.util.waterbutler.create_folder')
    def test_create_wiki_folder_fail(self, mock_create_folder):
        mock_response = {
            'data': {
                'id': 'osfstorage/xxyyzz/',
                'attributes': {
                    'path': '/xxyyzz/'
                }
            }
        }
        mock_create_folder.return_value = MockResponse(mock_response, 400)

        osf_cookie = self.osf_cookie
        p_guid = self.guid
        folder_name = 'Wiki images'
        parent_path = 'osfstorage/'
        try:
            views._create_wiki_folder(osf_cookie, p_guid, folder_name, parent_path)
        except HTTPError as e:
            assert_equal('Error when create wiki folder', e.data['message_short'])
            assert_in('An error occures when create wiki folder', e.data['message_long'])

    @mock.patch('requests.get')
    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_get_md_content_from_wb_success(self, mock_task, mock_get):
        mock_response = b'test content'
        mock_get.return_value = MockWbResponse(mock_response, 200)
        mock_task.is_aborted.return_value = False
        data = [{'wiki_name': 'wikipage1', '_id': 'qwe'}]
        creator, creator_auth = get_creator_auth_header(self.user)
        result = views._get_md_content_from_wb(data, self.project, creator_auth, mock_task)
        assert_equal(result[0]['wiki_content'], 'test content')

    @mock.patch('requests.get')
    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_get_md_content_from_wb_fail(self, mock_task, mock_get):
        mock_response = {}
        mock_get.return_value = MockWbResponse(mock_response, 400)
        mock_task.is_aborted.return_value = False
        data = [{'wiki_name': 'wikipage2', '_id': 'rty'}]
        creator, creator_auth = get_creator_auth_header(self.user)
        result = views._get_md_content_from_wb(data, self.project, creator_auth, mock_task)
        assert_equal(result, [{'wiki_name': 'wikipage2', '_id': 'rty'}])

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_get_md_content_from_wb_aborted(self, mock_task):
        mock_task.is_aborted.return_value = True
        data = [{'wiki_name': 'wikipage1', '_id': 'qwe'}]
        creator, creator_auth = get_creator_auth_header(self.user)
        result = views._get_md_content_from_wb(data, self.project, creator_auth, mock_task)
        assert_is_none(result)

    @mock.patch('addons.wiki.utils.copy_files_with_timestamp')
    @mock.patch('osf.models.BaseFileNode')
    def test_wiki_copy_import_directory(self, mock_base_file_node, mock_clone):
        mock_base_file_node_instance = mock.Mock()
        mock_base_file_node_instance._id = 'ddeeff'
        mock_base_file_node.objects.get.return_value = mock_base_file_node_instance
        mock_cloned = mock.Mock()
        mock_cloned._id = 'ddeeff'
        mock_clone.return_value = mock_cloned
        node = NodeFactory(parent=self.project, creator=self.user)
        expected_id = 'ddeeff'
        cloned_id = views._wiki_copy_import_directory(self.project, self.copy_to_dir._id, self.root_import_folder1._id, node)
        assert_equal(expected_id, cloned_id)

    def test_different_depth(self):
        wiki_infos = [
            {'path': '/page1/page2/page3'},
            {'path': '/page4/page5'},
            {'path': '/page6'}
        ]
        max_depth = views._get_max_depth(wiki_infos)
        assert_equal(max_depth, 2)

    def test_non_empty_return(self):
        wiki_infos = [{'path': '/path1'}, {'path': '/path2'}, {'path': '/path3'}]
        imported_list = [{'path': '/path1'}]
        import_errors = views._create_import_error_list(wiki_infos, imported_list)
        assert_in('/path2', import_errors)
        assert_in('/path3', import_errors)

    def test_err_with_tab(self):
        err_obj = {'message_short': 'Error Message with Tab', 'message_long': '\tAn error occures with tab\t', 'code': 400, 'referrer': None}
        err_obj_con = 'code=400, data=' + json.dumps(err_obj)
        err = CeleryError(err_obj_con)
        expected_msg = 'An error occures with tab'
        result_msg = views._extract_err_msg(err)
        assert_equal(result_msg, expected_msg)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult.abort')
    def test_project_clean_celery_task_one_running_task(self, mock_abort):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-11', status=WikiImportTask.STATUS_COMPLETED, creator=self.user)
        WikiImportTask.objects.create(node=self.project, task_id='task-id-2222', status=WikiImportTask.STATUS_RUNNING, creator=self.user)
        url = self.project.api_url_for('project_clean_celery_tasks')
        res = self.app.post(url, auth=self.user.auth)
        task_completed = WikiImportTask.objects.get(task_id='task-id-11')
        task_running = WikiImportTask.objects.get(task_id='task-id-2222')
        assert_equal(task_completed.status, 'Completed')
        assert_equal(task_running.status, 'Stopped')
        mock_abort.assert_called()

    def test_get_abort_wiki_import_result_already_aborted(self):
        WikiImportTask.objects.create(
            node=self.project,
            task_id='task-id-5555',
            status=WikiImportTask.STATUS_STOPPED,
            process_end=datetime.datetime(2024, 5, 1, 11, 00, tzinfo=pytz.utc),
            creator=self.user
        )
        WikiImportTask.objects.create(
            node=self.project,
            task_id='task-id-6666',
            status=WikiImportTask.STATUS_STOPPED,
            process_end=datetime.datetime(2024, 5, 1, 9, 00, tzinfo=pytz.utc),
            creator=self.user
        )
        url = self.project.api_url_for('project_get_abort_wiki_import_result')
        response = self.app.get(url, auth=self.user.auth)
        json_string = response._app_iter[0].decode('utf-8')
        result = json.loads(json_string)
        assert_equal(result, {'aborted': True})

    def test_check_running_task_two(self):
        WikiImportTask.objects.create(
            node=self.project,
            task_id='task-id-aaaa',
            status=WikiImportTask.STATUS_RUNNING,
            creator=self.user
        )
        WikiImportTask.objects.create(
            node=self.project,
            task_id='task-id-bbbb',
            status=WikiImportTask.STATUS_RUNNING,
            creator=self.user
        )
        with assert_raises(HTTPError) as cm:
            views.check_running_task('task-id-aaaa', self.project)
        # HTTPErrorの中身がWIKI_IMPORT_TASK_ALREADY_EXISTSのメッセージを持つか確認
        assert_equal(cm.exception.data['message_short'], 'Running Task exists')
        assert_equal(cm.exception.data['message_long'], '\tOnly 1 wiki import task can be executed on 1 node\t')
        task_running = WikiImportTask.objects.get(task_id='task-id-aaaa')
        assert_equal(task_running.status, 'Error')

    @freeze_time('2024-05-01 12:00:00')
    def test_change_task_status(self):
        WikiImportTask.objects.create(
            node=self.project,
            task_id='task-id-cccc',
            status=WikiImportTask.STATUS_COMPLETED,
            creator=self.user
        )
        views.change_task_status('task-id-cccc', WikiImportTask.STATUS_COMPLETED, True)
        task_running = WikiImportTask.objects.get(task_id='task-id-cccc')
        assert_equal(task_running.status, 'Completed')
        assert_equal(task_running.process_end, timezone.make_aware(datetime.datetime(2024, 5, 1, 12, 0, 0)))

    def test_set_wiki_import_task_proces_end_no_tasks_to_update(self):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-11111', status=WikiImportTask.STATUS_COMPLETED, creator=self.user)
        views.set_wiki_import_task_proces_end(self.project)
        assert_equal(WikiImportTask.objects.count(), 1)

    def test_project_update_wiki_page_sort(self):
        url = self.project.api_url_for('project_update_wiki_page_sort')
        respose = self.app.post_json(url,
            {
                'sortedData': [
                    {
                        'name': 'importpagea1',
                        'id': self.guid1,
                        'sortOrder': 1,
                        'children': [],
                        'fold': False
                    },
                    {
                        'name': 'importpageb2',
                        'id': self.guid2,
                        'sortOrder': 2,
                        'children': [
                            {
                                'name': 'wiki child page1',
                                'id': self.child_guid1,
                                'sortOrder': 1,
                                'children': [],
                                'fold': False
                            },
                            {
                                'name': 'wiki child page2',
                                'id': self.child_guid2,
                                'sortOrder': 2,
                                'children': [
                                    {
                                        'name': 'wiki child page3',
                                        'id': self.child_guid3,
                                        'sortOrder': 1,
                                        'children': [],
                                        'fold': False
                                    }
                                ],
                                'fold': False
                            }
                        ],
                        'fold': False
                    }
                ]
            },
            auth=self.auth
        )
        page_names = ['importpagea1', 'importpageb2', 'wiki child page1', 'wiki child page2', 'wiki child page3']
        result_list = list(WikiPage.objects.filter(page_name__in=page_names).order_by('page_name').values_list('page_name', 'parent_id', 'sort_order'))
        expected_list = [
            ('importpagea1', None, 1),
            ('importpageb2', None, 2),
            ('wiki child page1', self.wiki_page2.id, 1),
            ('wiki child page2', self.wiki_page2.id, 2),
            ('wiki child page3', self.wiki_child_page2.id, 1)
        ]
        assert_equal(expected_list, result_list)

    def test_sorted_data_nest(self):
        # TODO: 本質的に不要 削除する
        sorted_data = [{'name': 'tsta', 'id': '97xuz', 'sortOrder': 1, 'children': [], 'fold': False}, {'name': 'tstb', 'id': 'gwd9u', 'sortOrder': 2, 'children': [{'name': 'child1', 'id': '5fhdq', 'sortOrder': 1, 'children': [], 'fold': False}, {'name': 'child2', 'id': 'x38vh', 'sortOrder': 2, 'children': [{'name': 'grandchilda', 'id': '64au2', 'sortOrder': 1, 'children': [], 'fold': False}], 'fold': False}], 'fold': False}]
        id_list, sort_list, parent_wiki_id_list = views._get_sorted_list(sorted_data, None)
        assert_equal(id_list, ['97xuz', 'gwd9u', '5fhdq', 'x38vh', '64au2'])
        assert_equal(sort_list, [1, 2, 1, 2, 1])
        assert_equal(parent_wiki_id_list, [None, None, 'gwd9u', 'gwd9u', 'x38vh'])

    def test_bulk_update_wiki_sort(self):
        # TODO: 本質的に不要 削除する
        sort_id_list = [self.guid1, self.guid2, self.child_guid2, self.child_guid3, self.child_guid1]
        sort_num_list = [1, 2, 1, 2, 3]
        parent_wiki_id_list = [None, None, self.guid2, self.child_guid2, None]
        views._bulk_update_wiki_sort(self.project, sort_id_list, sort_num_list, parent_wiki_id_list)

        page_names = ['importpagea1', 'importpageb2', 'wiki child page1', 'wiki child page2', 'wiki child page3']
        result_list = list(WikiPage.objects.filter(page_name__in=page_names).order_by('page_name').values_list('page_name', 'parent_id', 'sort_order'))
        expected_list = [
            ('importpagea1', None, 1),
            ('importpageb2', None, 2),
            ('wiki child page1', None, 3),
            ('wiki child page2', self.wiki_page2.id, 1),
            ('wiki child page3', self.wiki_child_page2.id, 2)
        ]
        assert_equal(expected_list, result_list)

    # 編集権限がある場合の正常系テスト
    def test_valid_view_with_edit_permission(self):
        auth = self.auth
        node = self.node
        kwargs = {'node': node}

        result = views.project_wiki_view(auth, 'home', **kwargs)
        # 編集権限があるため、can_edit_wiki_body は True
        assert_true(result['user']['can_edit_wiki_body'])
        assert_equal('home', result['wiki_name'])

    # wiki_page が存在せず、wiki_key が home 以外 → WIKI_PAGE_NOT_FOUND_ERROR を発生させる
    def test_wiki_page_not_found_error(self):
        auth = self.consolidate_auth
        node = self.node
        kwargs = {'node': node}

        with assert_raises(self.WIKI_PAGE_NOT_FOUND_ERROR):
            views.project_wiki_view(auth, 'NotHome', **kwargs)

    # 'edit' が args に含まれ、公開編集が有効 → 401 エラー
    def test_edit_arg_public_editable_unauthorized(self):
        auth = self.auth
        node = self.node
        kwargs = {'node': node, 'edit': True}
        wiki_settings = node.get_addon('wiki')
        wiki_settings.is_publicly_editable = True
        wiki_settings.save()

        with assert_raises(Exception) as excinfo:
            views.project_wiki_view(auth, 'home', **kwargs)
        assert excinfo.value.code == http_status.HTTP_401_UNAUTHORIZED

    # 'edit' が args に含まれ、閲覧可能 → リダイレクト
    def test_edit_arg_redirect_if_can_view(self):
        auth = self.auth
        node = self.node
        kwargs = {'node': node, 'edit': True}

        result = views.project_wiki_view(auth, 'home', **kwargs)
        # リダイレクトオブジェクトが返ることを確認（簡易的にURLを確認）
        assert '/web/wiki' in result.headers['Location']

    # 'edit' が args に含まれ、閲覧不可 → 403 エラー
    def test_edit_arg_forbidden_if_cannot_view(self):
        user = AuthUserFactory()
        auth = user.auth
        node = self.node
        kwargs = {'node': node, 'edit': True}

        with assert_raises(Exception) as excinfo:
            views.project_wiki_view(auth, 'home', **kwargs)
        assert excinfo.value.code == http_status.HTTP_403_FORBIDDEN

    # format_wiki_version が例外を投げる → WIKI_INVALID_VERSION_ERROR を発生させる
    @mock.patch('addons.wiki.utils.format_wiki_version')
    def test_invalid_version_exception(self, mock_format_wiki_version):
        format_wiki_version.side_effect = InvalidVersionError
        auth = self.auth
        node = self.node
        kwargs = {'node': node}

        with assert_raises(Exception) as excinfo:
            views.project_wiki_view(auth, 'home', **kwargs)
        assert_equal(self.WIKI_INVALID_VERSION_ERROR.message_short, excinfo.message_short)
