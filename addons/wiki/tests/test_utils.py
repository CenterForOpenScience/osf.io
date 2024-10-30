# -*- coding: utf-8 -*-
# TODO: Port to pytest
# PEP8 asserts
from copy import deepcopy
from rest_framework import status as http_status
import json
import time
import mock
import pytest
import pytz
import datetime
import unicodedata
import uuid
from nose.tools import *  # noqa
from unittest.mock import MagicMock
from tests.base import OsfTestCase, fake
from osf_tests.factories import (
    UserFactory, NodeFactory, ProjectFactory,
    AuthUserFactory, RegistrationFactory
)
from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory

from osf.exceptions import NodeStateError
from osf.utils.permissions import ADMIN, WRITE, READ
from osf.models import BaseFileNode, File, Folder
from addons.wiki import settings
from addons.wiki import views
from addons.wiki.exceptions import InvalidVersionError
from addons.wiki.models import WikiPage, WikiVersion, render_content
from addons.wiki.utils import (
    get_sharejs_uuid, generate_private_uuid, share_db, delete_share_doc,
    migrate_uuid, format_wiki_version, serialize_wiki_settings, serialize_wiki_widget,
    check_file_object_in_node, get_numbered_name_for_existing_wiki, get_import_wiki_name_list,
    get_wiki_fullpath, _get_wiki_parent, _get_all_child_file_ids, get_node_file_mapping
)
from addons.wiki import tasks
from framework.auth import Auth
from django.utils import timezone
from addons.wiki.utils import to_mongo_key

from .config import EXAMPLE_DOCS, EXAMPLE_OPS

from framework.exceptions import HTTPError

pytestmark = pytest.mark.django_db

import logging
logger = logging.getLogger(__name__)

class TestWikiUtils(OsfTestCase):

    def setUp(self):
        super(TestWikiViews, self).setUp()

class TestFileNode(BaseFileNode):
    _provider = 'test',

class TestFile(TestFileNode, File):
    pass

class TestFolder(TestFileNode, Folder):
    pass

class MockResponse:
    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError('HTTPError')

    def json(self):
        return self.content

class MockWbResponse:
    def __init__(self, content, status_code):
        self._content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError('HTTPError')

    def json(self):
        return self._content

class MockTaskResponse:
    def __init__(self, content):
        self.ready = False

    def ready(self):
        return self.ready

class TestCheckFileObjectInNode(OsfTestCase):

    def setUp(self):
        super(TestCheckFileObjectInNode, self).setUp()
        self.user = AuthUserFactory()
        self.project1 = ProjectFactory(is_public=True, creator=self.user)
        self.project2 = ProjectFactory(is_public=True, creator=self.user)
        self.folder1 = TestFolder.objects.create(name='folder1', target=self.project1)
        self.folder2 = TestFolder.objects.create(name='folder2', target=self.project2)

    def test_correct_directory_id(self):
        dir_id = self.folder1._id
        result = check_file_object_in_node(dir_id, self.project1)
        self.assertTrue(result)

    def test_invalid_directory_id(self):
        with self.assertRaises(HTTPError) as context:
            check_file_object_in_node('invalid_directory_id', self.project1)

        self.assertEqual(context.exception.data['message_short'], 'directory id does not exist')
        self.assertEqual(context.exception.data['message_long'], 'directory id does not exist')

    def test_invalid_target_object_id(self):
        dir_id = self.folder1._id
        with self.assertRaises(HTTPError) as context:
            check_file_object_in_node(dir_id, self.project2)

        self.assertEqual(context.exception.data['message_short'], 'directory id is invalid')
        self.assertEqual(context.exception.data['message_long'], 'directory id is invalid')

class TestGetWikiFullpath(OsfTestCase):

    def setUp(self):
        super(TestGetWikiFullpath, self).setUp()

        creator = AuthUserFactory()
        self.user = creator

        self.project = ProjectFactory(is_public=True, creator=creator)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.auth = creator.auth
        self.no_parent_wiki = WikiPage.objects.create_for_node(self.project, 'No Parent Wiki', 'This is no parent wiki', self.consolidate_auth)
        self.parent_wiki = WikiPage.objects.create_for_node(self.project, 'Parent Wiki', 'This is parent wiki', self.consolidate_auth)
        self.child_wiki = WikiPage.objects.create_for_node(self.project, 'Child Wiki', 'This is child wiki', self.consolidate_auth, parent=self.parent_wiki)
        self.home_wiki = WikiPage.objects.create_for_node(self.project, 'home', 'This is home wiki', self.consolidate_auth)
        self.home_child_wiki = WikiPage.objects.create_for_node(self.project, 'home child', 'This is home child wiki', self.consolidate_auth, parent=self.home_wiki )

    def test_no_parent(self):
        wiki = self.no_parent_wiki
        wiki_name = wiki.page_name
        result = _get_wiki_parent(wiki, wiki_name)
        self.assertEqual(result, wiki_name)

    def test_with_parent(self):
        wiki = self.child_wiki
        parent_wiki_name = self.parent_wiki.page_name
        wiki_name = wiki.page_name
        expected_path = parent_wiki_name + '/' + wiki_name
        result = _get_wiki_parent(wiki, wiki_name)
        self.assertEqual(result, expected_path)

    def test_with_home_parent(self):
        wiki = self.home_child_wiki
        parent_wiki_name = self.home_wiki.page_name
        wiki_name = wiki.page_name
        expected_result = 'HOME/' + wiki_name
        result = _get_wiki_parent(wiki, wiki_name)
        self.assertEqual(result, expected_result)

    def test_existing_wiki(self):
        wiki = self.child_wiki
        parent_wiki_name = self.parent_wiki.page_name
        wiki_name = wiki.page_name
        expected_result = '/' + parent_wiki_name + '/' + wiki_name
        result = get_wiki_fullpath(self.project, wiki_name)
        self.assertEqual(result, expected_result)

    def test_non_existing_wiki(self):
        result = get_wiki_fullpath(self.project, 'non existing wiki name')
        self.assertEqual(result, '')

class TestGetNumberedNameForExistingWiki(OsfTestCase):

    def setUp(self):
        super(TestGetNumberedNameForExistingWiki, self).setUp()

        creator = AuthUserFactory()
        self.user = creator

        self.project = ProjectFactory(is_public=True, creator=creator)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.auth = creator.auth
        self.existing_wiki = WikiPage.objects.create_for_node(self.project, 'Existing Wiki', 'This is no existing wiki', self.consolidate_auth)
        self.home_wiki = WikiPage.objects.create_for_node(self.project, 'home', 'This is home wiki', self.consolidate_auth)
        self.wiki_no_numbered = WikiPage.objects.create_for_node(self.project, 'Numbered', 'This is numbered wiki', self.consolidate_auth)
        self.wiki_numbered = WikiPage.objects.create_for_node(self.project, 'Numbered(1)', 'This is numbered wiki(1)', self.consolidate_auth)

    def test_no_matching_wiki(self):
        base_name = 'test'
        result = get_numbered_name_for_existing_wiki(self.project, base_name)
        self.assertEqual(result, '')

    def test_matching_wiki_no_number(self):
        base_name = 'Existing Wiki'
        result = get_numbered_name_for_existing_wiki(self.project, base_name)
        self.assertEqual(result, 1)

    def test_matching_wiki_with_number(self):
        base_name = 'Numbered'
        result = get_numbered_name_for_existing_wiki(self.project, base_name)
        self.assertEqual(result, 2)

    def test_matching_wiki_home(self):
        result = get_numbered_name_for_existing_wiki(self.project, 'home')
        self.assertEqual(result, 1)

class TestGetImportWikiNameList(OsfTestCase):

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
        self.assertEqual(result, expected_result)

class TestGetNodeFileMapping(OsfTestCase):
    def setUp(self):
        super(TestGetNodeFileMapping, self).setUp()
        self.user = AuthUserFactory()
        self.project1 = ProjectFactory(is_public=True, creator=self.user)
        self.consolidate_auth = Auth(user=self.project1.creator)
        self.wiki_import_dir = TestFolder.objects.create(name='wiki import dir', target=self.project1)
        self.pagefolder1 = TestFolder.objects.create(name='page1', target=self.project1, parent=self.wiki_import_dir)
        self.pagefolder2 = TestFolder.objects.create(name='page2', target=self.project1, parent=self.wiki_import_dir)
        self.pagefile1 = TestFile.objects.create(name='page1.md', target=self.project1, parent=self.pagefolder1)
        self.attachment1 = TestFile.objects.create(name='attachment1.pdf', target=self.project1, parent=self.pagefolder1)
        self.pagefile2 = TestFile.objects.create(name='page2.md', target=self.project1, parent=self.pagefolder2)
        self.attachment2 = TestFile.objects.create(name='attachment2.docx', target=self.project1, parent=self.pagefolder2)
        self.pagefolder3 = TestFolder.objects.create(name='page3', target=self.project1, parent=self.pagefolder2)
        self.pagefile3 = TestFile.objects.create(name='page3.md', target=self.project1, parent=self.pagefolder3)
        self.attachment3 = TestFile.objects.create(name='attachment3.xlsx', target=self.project1, parent=self.pagefolder3)

    @mock.patch('addons.wiki.views.BaseFileNode.objects.filter')
    def test_get_node_file_mapping(self, mock_filter):

        mock_filter.return_value.values_list.return_value = [
            (self.pagefile1._id, 'page1.md', 'page1'),
            (self.attachment1._id, 'attachment1.pdf', 'page1'),
            (self.pagefile2._id, 'page2.md', 'page2'),
            (self.attachment2._id, 'attachment2.docx', 'page2'),
            (self.pagefile3._id, 'page3.md', 'page3'),
            (self.attachment3._id, 'attachment3.xlsx', 'page3'),
        ]
        file_mapping = get_node_file_mapping(self.project1, self.wiki_import_dir._id)
        expected_mapping = {
            'page1^page1.md': self.pagefile1._id,
            'page1^attachment1.pdf': self.attachment1._id,
            'page2^page2.md': self.pagefile2._id,
            'page2^attachment2.docx': self.attachment2._id,
            'page3^page3.md': self.pagefile3._id,
            'page3^attachment3.xlsx': self.attachment3._id,
        }

        self.assertEqual(file_mapping, expected_mapping)
