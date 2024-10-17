# -*- coding: utf-8 -*-
# TODO: Port to pytest
# PEP8 asserts
from copy import deepcopy
from rest_framework import status as http_status
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
    check_file_object_in_node
)
from addons.wiki import tasks
from framework.auth import Auth
from django.utils import timezone
from addons.wiki.utils import to_mongo_key

from .config import EXAMPLE_DOCS, EXAMPLE_OPS

pytestmark = pytest.mark.django_db

import logging
logger = logging.getLogger(__name__)

class TestWikiTasks(OsfTestCase):

    def setUp(self):
        super(TestWikiTasks, self).setUp()

        creator = AuthUserFactory()
        self.user = creator

        self.project = ProjectFactory(is_public=True, creator=creator)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.auth = creator.auth
        self.home_wiki = WikiPage.objects.create_for_node(self.project, 'home', 'This is home wiki', self.consolidate_auth)
        self.wiki_page1 = WikiPage.objects.create_for_node(self.project, 'page1', 'This is a wiki page1', self.consolidate_auth)
        self.wiki_page2 = WikiPage.objects.create_for_node(self.project, 'page2', 'This is a wiki page2', self.consolidate_auth)
        self.wiki_page3 = WikiPage.objects.create_for_node(self.project, 'page3', 'This is a wiki page3', self.consolidate_auth, self.wiki_page2)

    @mock.patch('website.project.decorators._load_node_or_fail')
    @mock.patch('addons.wiki.views.project_wiki_validate_for_import_process')
    def test_project_wiki_validate_for_import_task_called(self, mock_process, mock_load_node):
        mock_load_node.return_value = 'testttt'
        result = tasks.run_project_wiki_validate_for_import.apply_async(('dir_id', 'node_id'))
        result.wait()
        self.assertTrue(result.called)
        mock_process.assert_called_once_with('dir_id', self.project)

    @mock.patch('website.project.decorators._load_node_or_fail')
    @mock.patch('addons.wiki.views.project_wiki_import_process')
    def test_project_wiki_import_task_called(self, mock_process, mock_load_node):
        data_json = [
            {
                'parent_wiki_name': None,
                'path': '/page1',
                'original_name': 'page1',
                'wiki_name': 'page1',
                'status': 'valid',
                'message': '',
                '_id': 'xxx',
                'wiki_content': 'content1'
            }
        ]
        dir_id = 'dir_id'
        current_user_id = 'user_id'
        nid = 'node_id'
        mock_node = mock_load_node.return_value
        mock_user = mock_load_user.return_value
        result = tasks.run_project_wiki_import.apply_async((data_json, dir_id, current_user_id, nid))
        result.wait()
        self.assertTrue(result.called)
        mock_process.assert_called_once_with(data_json, dir_id, result.id, mock_node)

    @mock.patch('website.project.decorator._load_node_or_fail')
    @mock.patch('website.search.elastic_search.bulk_update_wikis')
    @mock.patch('addons_wiki.models.WikiPage.objects.filter')
    def test_update_search_and_bulk_index(self, mock_filter, mock_bulk_update_wikis, mock_load_node_or_fail):
        # モックデータ
        nid = 'node_id'
        wiki_id_list = [1, 2, 3]
        # モックの設定
        mock_node = mock_load_node_or_fail.return_value
        mock_filter.return_value = [self.wiki_page1, self.wiki_page2]
        # テスト対象の関数を実行
        run_update_search_and_bulk_index(nid, wiki_id_list)

        result = tasks.run_update_search_and_bulk_index.apply_async((nid, wiki_id_list))
        result.wait()
        self.assertTrue(result.called)
        mock_bulk_update_wikis.assert_called_once_with(mock_wiki_pages)
        mock_node.update_search.assert_called_once()


