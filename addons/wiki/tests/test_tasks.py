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
from unittest.mock import MagicMock, ANY
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
from website.project.decorators import _load_node_or_fail
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

    @mock.patch('addons.wiki.views.project_wiki_validate_for_import_process')
    def test_project_wiki_validate_for_import_task_called(self, mock_process):
        nid = self.project.guids.first()._id
        node = _load_node_or_fail(nid)
        result = tasks.run_project_wiki_validate_for_import.apply_async(('dir_id', nid))
        result.wait()
        self.assertTrue(result.successful())
        mock_process.assert_called_once_with('dir_id', node)

    @mock.patch('addons.wiki.views.project_wiki_import_process')
    def test_project_wiki_import_task_called(self, mock_process):
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
        data_json_str = json.dumps(data_json)
        current_user_id = self.user._id
        dir_id = 'dir_id'
        nid = self.project.guids.first()._id
        node = _load_node_or_fail(nid)
        auth = self.consolidate_auth
        result = tasks.run_project_wiki_import.apply_async((data_json_str, dir_id, current_user_id, nid))
        result.wait()
        self.assertTrue(result.successful())

        mock_process.assert_called_once_with(data_json, dir_id, result.id, ANY, node)
        self.assertEqual(mock_process.call_args[0][3].user._id, auth.user._id)

    @mock.patch('osf.models.Node.update_search')
    def test_update_search_and_bulk_index(self, mock_update_search):
        nid = self.project.guids.first()._id
        wiki_id_list = [self.wiki_page1.id, self.wiki_page2.id, self.wiki_page3.id]

        result = tasks.run_update_search_and_bulk_index.apply_async((nid, wiki_id_list))
        result.wait()
        self.assertTrue(result.successful())
        # Indirectly test bulk_update_wikis by verifying the search results on the screen after saving the Wiki page.
        mock_update_search.assert_called_once()


