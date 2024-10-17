# -*- coding: utf-8 -*-
# TODO: Port to pytest
from celery.exceptions import CeleryError
from framework.exceptions import HTTPError
from freezegun import freeze_time
import json
# PEP8 asserts
from copy import deepcopy
from rest_framework import status as http_status
import time
import mock
import pytest
import pytz
import datetime
import re
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
from addons.wiki.tests.test_utils import MockTaskResponse, MockWbResponse, MockResponse, TestFile, TestFolder
from osf.exceptions import NodeStateError
from osf.utils.permissions import ADMIN, WRITE, READ
from osf.models import BaseFileNode, File, Folder
from osf.management.commands.import_EGAP import get_creator_auth_header
from addons.wiki import settings
from addons.wiki import views
from addons.wiki.exceptions import InvalidVersionError
from addons.wiki.models import WikiImportTask, WikiPage, WikiVersion, render_content
from addons.wiki.utils import (
    get_sharejs_uuid, generate_private_uuid, share_db, delete_share_doc,
    migrate_uuid, format_wiki_version, serialize_wiki_settings, serialize_wiki_widget,
    check_file_object_in_node
)
from addons.wiki.views import WIKI_IMPORT_TASK_ALREADY_EXISTS
from addons.wiki import tasks
from framework.auth import Auth
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from addons.wiki.utils import to_mongo_key
from website import settings as website_settings
from .config import EXAMPLE_DOCS, EXAMPLE_OPS

pytestmark = pytest.mark.django_db
from osf.management.commands.import_EGAP import get_creator_auth_header
from addons.wiki.exceptions import ImportTaskAbortedError
from addons.osfstorage.models import OsfStorageFolder, OsfStorageFile
from django.test import override_settings
import logging
logger = logging.getLogger(__name__)

# forward slashes are not allowed, typically they would be replaced with spaces
SPECIAL_CHARACTERS_ALL = u'`~!@#$%^*()-=_+ []{}\|/?.df,;:''"'
SPECIAL_CHARACTERS_ALLOWED = u'`~!@#$%^*()-=_+ []{}\|?.df,;:''"'

@pytest.mark.enable_bookmark_creation
class TestWikiViews(OsfTestCase):

    def setUp(self):
        super(TestWikiViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.home_wiki = WikiPage.objects.create_for_node(self.project, 'home', 'Version 1', Auth(self.user))
        self.home_wiki.update(self.user, 'Version 2')
        self.funpage_wiki = WikiPage.objects.create_for_node(self.project, 'funpage', 'Version 1', Auth(self.user))

        self.second_project = ProjectFactory(is_public=True, creator=self.user)
        self.sec_wiki = WikiPage.objects.create_for_node(self.second_project, 'home', '', Auth(self.user))

    def test_wiki_url_get_returns_200(self):
        url = self.project.web_url_for('project_wiki_view', wname='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_url_404_with_no_write_permission(self):  # and not public
        url = self.project.web_url_for('project_wiki_view', wname='somerandomid')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_wiki_deleted_404_with_no_write_permission(self, mock_sharejs):
        url = self.project.web_url_for('project_wiki_view', wname='funpage')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        delete_url = self.project.api_url_for('project_wiki_delete', wname='funpage')
        self.app.delete(delete_url, auth=self.user.auth)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_wiki_url_with_path_get_returns_200(self):
        self.funpage_wiki.update(self.user, 'Version 2')

        url = self.project.web_url_for(
            'project_wiki_view',
            wname='funpage',
        ) + '?view&compare=1&edit'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_wiki_url_with_edit_get_redirects_to_no_edit_params_with_no_write_permission(self):
        self.funpage_wiki.update(self.user, 'Version 2')

        url = self.project.web_url_for(
            'project_wiki_view',
            wname='funpage',
            compare=1,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        # Public project, can_view, redirects without edit params
        url = self.project.web_url_for(
            'project_wiki_view',
            wname='funpage',
        ) + '?edit'
        res = self.app.get(url).maybe_follow()
        assert_equal(res.status_code, 200)

        # Check publicly editable
        wiki = self.project.get_addon('wiki')
        wiki.set_editing(permissions=True, auth=self.consolidate_auth, log=True)
        res = self.app.get(url, auth=AuthUserFactory().auth, expect_errors=False)
        assert_equal(res.status_code, 200)

        # Check publicly editable but not logged in
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_wiki_url_for_pointer_returns_200(self):
        # TODO: explain how this tests a pointer
        project = ProjectFactory(is_public=True)
        self.project.add_pointer(project, Auth(self.project.creator), save=True)
        url = self.project.web_url_for('project_wiki_view', wname='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    @pytest.mark.skip('#TODO: Fix or mock mongodb for sharejs')
    def test_wiki_draft_returns_200(self):
        url = self.project.api_url_for('wiki_page_draft', wname='somerandomid')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_wiki_content_returns_200(self):
        url = self.project.api_url_for('wiki_page_content', wname='somerandomid')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    @mock.patch('addons.wiki.models.WikiVersion.rendered_before_update', new_callable=mock.PropertyMock)
    def test_wiki_content_rendered_before_update(self, mock_rendered_before_update):
        content = 'Some content'
        WikiPage.objects.create_for_node(self.project, 'somerandomid', content, Auth(self.user))

        mock_rendered_before_update.return_value = True
        url = self.project.api_url_for('wiki_page_content', wname='somerandomid')
        res = self.app.get(url, auth=self.user.auth)
        assert_true(res.json['rendered_before_update'])

        mock_rendered_before_update.return_value = False
        res = self.app.get(url, auth=self.user.auth)
        assert_false(res.json['rendered_before_update'])

    def test_wiki_url_for_component_returns_200(self):
        component = NodeFactory(parent=self.project, is_public=True)
        url = component.web_url_for('project_wiki_view', wname='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_project_wiki_edit_post(self):
        url = self.project.web_url_for('project_wiki_edit_post', wname='home')
        res = self.app.post_json(url, {'markdown': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        # page was updated with new content
        new_wiki = WikiVersion.objects.get_for_node(self.project, 'home')
        assert_equal(new_wiki.content, 'new content')

    def test_project_wiki_edit_post_non_nfc_input(self):
        wname = 'new name'
        nfd_wname = unicodedata.normalize('NFD', wname)
        url = self.project.web_url_for('project_wiki_edit_post', wname=nfd_wname)
        wcontent = 'new content'
        nfd_content = unicodedata.normalize('NFD', wcontent)
        res = self.app.post_json(url, {'markdown': nfd_content}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        new_wiki = WikiPage.objects.get_for_node(self.project, wname)
        new_wiki_version = WikiVersion.objects.get_for_node(self.project, wname)
        assert_equal(new_wiki.page_name, unicodedata.normalize('NFC', wname))
        assert_equal(new_wiki_version.content, unicodedata.normalize('NFC', wcontent))

    def test_project_wiki_edit_post_with_new_wname_and_no_content(self):
        # note: forward slashes not allowed in page_name
        page_name = fake.catch_phrase().replace('/', ' ')
        old_wiki_page_count = WikiVersion.objects.all().count()
        url = self.project.web_url_for('project_wiki_edit_post', wname=page_name)
        # User submits to edit form with no content
        res = self.app.post_json(url, {'markdown': ''}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        new_wiki_page_count = WikiVersion.objects.all().count()
        # A new wiki page was created in the db
        assert_equal(new_wiki_page_count, old_wiki_page_count + 1)

        # Node now has the new wiki page associated with it
        self.project.reload()
        new_page =  WikiVersion.objects.get_for_node(self.project, page_name)
        assert_is_not_none(new_page)

    def test_project_wiki_edit_post_with_new_wname_and_content(self):
        # note: forward slashes not allowed in page_name
        page_name = fake.catch_phrase().replace('/', ' ')
        page_content = fake.bs()

        old_wiki_page_count = WikiVersion.objects.all().count()
        url = self.project.web_url_for('project_wiki_edit_post', wname=page_name)
        # User submits to edit form with no content
        res = self.app.post_json(url, {'markdown': page_content}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        new_wiki_page_count = WikiVersion.objects.all().count()
        # A new wiki page was created in the db
        assert_equal(new_wiki_page_count, old_wiki_page_count + 1)

        # Node now has the new wiki page associated with it
        self.project.reload()
        new_page =  WikiVersion.objects.get_for_node(self.project, page_name)
        assert_is_not_none(new_page)
        # content was set
        assert_equal(new_page.content, page_content)

    def test_project_wiki_edit_post_with_non_ascii_title(self):
        # regression test for https://github.com/CenterForOpenScience/openscienceframework.org/issues/1040
        # wname doesn't exist in the db, so it will be created
        new_wname = u'øˆ∆´ƒøßå√ß'
        url = self.project.web_url_for('project_wiki_edit_post', wname=new_wname)
        res = self.app.post_json(url, {'markdown': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        wiki = WikiPage.objects.get_for_node(self.project, new_wname)
        assert_equal(wiki.page_name, new_wname)

        # updating content should return correct url as well.
        res = self.app.post_json(url, {'markdown': 'updated content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

    def test_project_wiki_edit_post_with_special_characters(self):
        new_wname = 'title: ' + SPECIAL_CHARACTERS_ALLOWED
        new_wiki_content = 'content: ' + SPECIAL_CHARACTERS_ALL
        url = self.project.web_url_for('project_wiki_edit_post', wname=new_wname)
        res = self.app.post_json(url, {'markdown': new_wiki_content}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        wiki =  WikiVersion.objects.get_for_node(self.project, new_wname)
        assert_equal(wiki.wiki_page.page_name, new_wname)
        assert_equal(wiki.content, new_wiki_content)
        assert_equal(res.status_code, 200)

    def test_wiki_edit_get_home(self):
        url = self.project.web_url_for('project_wiki_view', wname='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_view_scope(self):
        url = self.project.web_url_for('project_wiki_view', wname='home', view=2)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        url = self.project.web_url_for('project_wiki_view', wname='home', view=3)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        url = self.project.web_url_for('project_wiki_view', wname='home', view=0)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_project_wiki_compare_returns_200(self):
        url = self.project.web_url_for('project_wiki_view', wname='home') + '?compare'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_compare_scope(self):
        url = self.project.web_url_for('project_wiki_view', wname='home', compare=2)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        url = self.project.web_url_for('project_wiki_view', wname='home', compare=3)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        url = self.project.web_url_for('project_wiki_view', wname='home', compare=0)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_wiki_page_creation_strips_whitespace(self):
        # Regression test for:
        # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1080
        # wname has a trailing space
        url = self.project.web_url_for('project_wiki_view', wname='cupcake ')
        res = self.app.post_json(url, {'markdown': 'blah'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        self.project.reload()
        wiki =  WikiVersion.objects.get_for_node(self.project, 'cupcake')
        assert_is_not_none(wiki)

    def test_wiki_validate_name(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='Capslock')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_wiki_validate_name_nfd(self):
        wiki_name_nfd = unicodedata.normalize('NFD', 'Capslock')
        url = self.project.api_url_for('project_wiki_validate_name', wname=wiki_name_nfd)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        wiki = WikiPage.objects.get_for_node(self.project, 'Capslock')
        assert_equal(WikiPage.objects.get_for_node(self.project, 'Capslock').page_name, 'Capslock')

    def test_wiki_validate_name_creates_blank_page(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='newpage', auth=self.consolidate_auth)
        self.app.get(url, auth=self.user.auth)
        self.project.reload()
        assert_is_not_none(WikiPage.objects.get_for_node(self.project, 'newpage'))

    def test_wiki_validate_name_collision_doesnt_clear(self):
        WikiPage.objects.create_for_node(self.project, 'oldpage', 'some text', self.consolidate_auth)
        url = self.project.api_url_for('project_wiki_validate_name', wname='oldpage', auth=self.consolidate_auth)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        url = self.project.api_url_for('wiki_page_content', wname='oldpage', auth=self.consolidate_auth)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['wiki_content'], 'some text')

    def test_wiki_validate_name_cannot_create_home(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='home')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_project_wiki_validate_name_mixed_casing(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='CaPsLoCk')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        wiki = WikiPage.objects.get_for_node(self.project, 'CaPsLoCk')
        assert_equal(WikiPage.objects.get_for_node(self.project, 'CaPsLoCk').page_name, 'CaPsLoCk')

    def test_project_wiki_validate_name_display_correct_capitalization(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='CaPsLoCk')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_in('CaPsLoCk', res)

    def test_project_wiki_validate_name_conflict_different_casing(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='CAPSLOCK')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        wiki = WikiPage.objects.get_for_node(self.project, 'CaPsLoCk')
        wiki.update(self.user, 'hello')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_project_wiki_validate_name_with_parent(self):
        WikiPage.objects.create_for_node(self.project, 'parent', '', Auth(self.user))
        url = self.project.api_url_for('project_wiki_validate_name', wname='child', p_wname='parent')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        parent = WikiPage.objects.get_for_node(self.project, 'parent')
        child = WikiPage.objects.get_for_node(self.project, 'child')
        assert_equal(parent, child.parent)

    def test_project_wiki_validate_name_invalid_parent(self):
        parent = WikiPage.objects.get_for_node(self.project, 'parent')
        assert_is_none(parent)
        url = self.project.api_url_for('project_wiki_validate_name', wname='child', p_wname='parent')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_project_wiki_validate_name_invalid_parent_default_home(self):
        project = ProjectFactory(creator=self.user)
        parent = WikiPage.objects.get_for_node(project, 'home')
        assert_is_none(parent)
        url = project.api_url_for('project_wiki_validate_name', wname='child', p_wname='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        parent = WikiPage.objects.get_for_node(project, 'home')
        child = WikiPage.objects.get_for_node(project, 'child')
        assert_equal(parent, child.parent)

    def test_project_wiki_validate_name_parent_default_home(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='child', p_wname='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        parent = WikiPage.objects.get_for_node(self.project, 'home')
        child = WikiPage.objects.get_for_node(self.project, 'child')
        assert_equal(parent, child.parent)

    def test_project_dashboard_shows_no_wiki_content_text(self):
        # Regression test for:
        # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1104
        project = ProjectFactory(creator=self.user)
        url = project.web_url_for('view_project')
        res = self.app.get(url, auth=self.user.auth)
        assert_in('Add important information, links, or images here to describe your project.', res)

    def test_project_dashboard_wiki_wname_get_shows_non_ascii_characters(self):
        # Regression test for:
        # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1104
        text = u'你好'
        self.home_wiki.update(self.user, text)

        # can view wiki preview from project dashboard
        url = self.project.web_url_for('view_project')
        res = self.app.get(url, auth=self.user.auth)
        assert_in(text, res)

    def test_project_wiki_home_api_route(self):
        url = self.project.api_url_for('project_wiki_home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.status_code, 302)
        # TODO: should this route exist? it redirects you to the web_url_for, not api_url_for.
        # page_url = self.project.api_url_for('project_wiki_view', wname='home')
        # assert_in(page_url, res.location)

    def test_project_wiki_home_web_route(self):
        page_url = self.project.web_url_for('project_wiki_view', wname='home', _guid=True)
        url = self.project.web_url_for('project_wiki_home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.status_code, 302)
        assert_in(page_url, res.location)

    def test_wiki_id_url_get_returns_302_and_resolves(self):
        name = 'page by id'
        page = WikiPage.objects.create_for_node(self.project, name, 'some content', Auth(self.project.creator))
        page_url = self.project.web_url_for('project_wiki_view', wname=page.page_name, _guid=True)
        url = self.project.web_url_for('project_wiki_id_page', wid=page._primary_key, _guid=True)
        res = self.app.get(url)
        assert_equal(res.status_code, 302)
        assert_in(page_url, res.location)
        res = res.follow()
        assert_equal(res.status_code, 200)
        assert_in(page_url, res.request.url)

    def test_wiki_id_url_get_returns_404(self):
        url = self.project.web_url_for('project_wiki_id_page', wid='12345', _guid=True)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_home_is_capitalized_in_web_view(self):
        url = self.project.web_url_for('project_wiki_home', wid='home', _guid=True)
        res = self.app.get(url, auth=self.user.auth).follow(auth=self.user.auth)
        page_name_elem = res.html.find('span', {'id': 'pageName'})
        assert_in('Home', page_name_elem.text)

    def test_wiki_widget_no_content(self):
        project = ProjectFactory(is_public=True, creator=self.user)
        res = serialize_wiki_widget(project)
        assert_is_none(res['wiki_content'])

    def test_wiki_widget_short_content_no_cutoff(self):
        short_content = 'a' * 150

        self.sec_wiki.update(self.user, short_content)
        res = serialize_wiki_widget(self.second_project)
        assert_in(short_content, res['wiki_content'])
        assert_not_in('...', res['wiki_content'])
        assert_false(res['more'])

    def test_wiki_widget_long_content_cutoff(self):
        long_content = 'a' * 600
        self.sec_wiki.update(self.user, long_content)
        res = serialize_wiki_widget(self.second_project)
        assert_less(len(res['wiki_content']), 520)  # wiggle room for closing tags
        assert_in('...', res['wiki_content'].decode())
        assert_true(res['more'])

    def test_wiki_widget_with_multiple_short_pages_has_more(self):
        project = ProjectFactory(is_public=True, creator=self.user)
        short_content = 'a' * 150
        self.sec_wiki.update(self.user, short_content)
        WikiPage.objects.create_for_node(self.second_project, 'andanotherone', short_content, Auth(self.user))
        res = serialize_wiki_widget(self.second_project)
        assert_true(res['more'])

    @mock.patch('addons.wiki.models.WikiVersion.rendered_before_update', new_callable=mock.PropertyMock)
    def test_wiki_widget_rendered_before_update(self, mock_rendered_before_update):
        # New pages use js renderer
        mock_rendered_before_update.return_value = False
        self.home_wiki.update(self.user, 'updated_content')
        res = serialize_wiki_widget(self.project)
        assert_false(res['rendered_before_update'])

        # Old pages use a different version of js render
        mock_rendered_before_update.return_value = True
        res = serialize_wiki_widget(self.project)
        assert_true(res['rendered_before_update'])

    def test_read_only_users_cannot_view_edit_pane(self):
        url = self.project.web_url_for('project_wiki_view', wname='home')
        # No write permissions
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_not_in('id="editWysiwyg"', res.text)
        assert_not_in('id="collaborativeStatus"', res.text)
        # Write permissions
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_in('id="editWysiwyg"', res.text)
        assert_in('id="collaborativeStatus"', res.text)
        # Publicly editable
        wiki = self.project.get_addon('wiki')
        wiki.set_editing(permissions=True, auth=self.consolidate_auth, log=True)
        res = self.app.get(url, auth=AuthUserFactory().auth)
        assert_equal(res.status_code, 200)
        assert_in('id="editWysiwyg"', res.text)
        assert_in('id="collaborativeStatus"', res.text)
        # Publicly editable but not logged in
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_not_in('id="editWysiwyg"', res.text)
        assert_not_in('id="collaborativeStatus"', res.text)

    def test_wiki_widget_not_show_in_registration_for_contributor(self):
        registration = RegistrationFactory(project=self.project)
        res = self.app.get(
            registration.web_url_for('view_project'),
            auth=self.user.auth
        )
        assert_equal(res.status_code, 200)
        assert_not_in('Add important information, links, or images here to describe your project.', res.text)

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
        self.assertEqual(result[0] , {'id': root_import_folder._id, 'name': 'rootimportfolder'})

class TestViewHelpers(OsfTestCase):

    def setUp(self):
        super(TestViewHelpers, self).setUp()
        self.project = ProjectFactory()
        self.wname = 'New page'
        wiki = WikiPage.objects.create_for_node(self.project, self.wname, 'some content', Auth(self.project.creator))

    def test_get_wiki_web_urls(self):
        urls = views._get_wiki_web_urls(self.project, self.wname)
        assert_equal(urls['base'], self.project.web_url_for('project_wiki_home', _guid=True))
        assert_equal(urls['edit'], self.project.web_url_for('project_wiki_view', wname=self.wname, _guid=True))
        assert_equal(urls['home'], self.project.web_url_for('project_wiki_home', _guid=True))
        assert_equal(urls['page'], self.project.web_url_for('project_wiki_view', wname=self.wname, _guid=True))

    def test_get_wiki_api_urls(self):
        urls = views._get_wiki_api_urls(self.project, self.wname)
        assert_equal(urls['base'], self.project.api_url_for('project_wiki_home'))
        assert_equal(urls['delete'], self.project.api_url_for('project_wiki_delete', wname=self.wname))
        assert_equal(urls['rename'], self.project.api_url_for('project_wiki_rename', wname=self.wname))
        assert_equal(urls['content'], self.project.api_url_for('wiki_page_content', wname=self.wname))
        assert_equal(urls['settings'], self.project.api_url_for('edit_wiki_settings'))


class TestWikiDelete(OsfTestCase):

    def setUp(self):
        super(TestWikiDelete, self).setUp()

        creator = AuthUserFactory()
        self.user = creator

        self.project = ProjectFactory(is_public=True, creator=creator)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.auth = creator.auth
        self.elephant_wiki = WikiPage.objects.create_for_node(self.project, 'Elephants', 'Hello Elephants', self.consolidate_auth)
        self.lion_wiki = WikiPage.objects.create_for_node(self.project, 'Lions', 'Hello Lions', self.consolidate_auth)
        self.koala_wiki = WikiPage.objects.create_for_node(self.project, 'Koalas', 'Hello Koalas', self.consolidate_auth)
        self.kangaroo_wiki = WikiPage.objects.create_for_node(self.project, 'kangaroos', 'Hello kangaroos', self.consolidate_auth, self.koala_wiki)
        self.giraffe_wiki = WikiPage.objects.create_for_node(self.project, 'Giraffes', 'Hello Giraffes', self.consolidate_auth)
        self.panda_wiki = WikiPage.objects.create_for_node(self.project, 'Pandas', 'Hello Pandas', self.consolidate_auth, self.giraffe_wiki)
        self.zebra_wiki = WikiPage.objects.create_for_node(self.project, 'Zebras', 'Hello Zebras', self.consolidate_auth, self.panda_wiki)

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_project_wiki_delete(self, mock_shrejs):
        page = self.elephant_wiki
        assert_equal(page.page_name.lower(), 'elephants')
        assert_equal(page.deleted, None)
        url = self.project.api_url_for(
            'project_wiki_delete',
            wname='Elephants'
        )
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.app.delete(
                url,
                auth=self.auth
            )
        self.project.reload()
        page.reload()
        assert_equal(page.deleted, mock_now)

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_project_wiki_delete_w_valid_special_characters(self, mock_sharejs):
        # TODO: Need to understand why calling update_node_wiki with failure causes transaction rollback issue later
        # with assert_raises(NameInvalidError):
        #     self.project.update_node_wiki(SPECIAL_CHARACTERS_ALL, 'Hello Special Characters', self.consolidate_auth)
        self.special_characters_wiki = WikiPage.objects.create_for_node(self.project, SPECIAL_CHARACTERS_ALLOWED, 'Hello Special Characters', self.consolidate_auth)
        assert_equal(self.special_characters_wiki.page_name, SPECIAL_CHARACTERS_ALLOWED)
        url = self.project.api_url_for(
            'project_wiki_delete',
            wname=SPECIAL_CHARACTERS_ALLOWED
        )
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.app.delete(
                url,
                auth=self.auth
            )
        self.project.reload()
        self.special_characters_wiki.reload()
        assert_equal(self.special_characters_wiki.deleted, mock_now)

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_wiki_versions_do_not_reappear_after_delete(self, mock_sharejs):
        # Creates a wiki page
        wiki_page = WikiPage.objects.create_for_node(self.project, 'Hippos', 'Hello hippos', self.consolidate_auth)
        # Edits the wiki
        assert_equal(wiki_page.deleted, None)
        assert_equal(wiki_page.current_version_number, 1)
        wiki_page.update(self.user, 'Hello hippopotamus')
        wiki_page.reload()
        assert_equal(wiki_page.current_version_number, 2)
        # Deletes the wiki page
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            wiki_page.delete(self.consolidate_auth)
        wiki_page.reload()
        assert_equal(wiki_page.deleted, mock_now)
        # Creates new wiki with same name as deleted wiki
        wiki_page = WikiPage.objects.create_for_node(self.project, 'Hippos', 'Hello again hippos', self.consolidate_auth)
        assert_equal(wiki_page.current_version_number, 1)
        wiki_page.update(self.user, 'Hello again hippopotamus')
        wiki_page.reload()
        assert_equal(wiki_page.current_version_number, 2)

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_project_wiki_delete_recursive_one_level(self, mock_shrejs):
        parent_wiki = self.koala_wiki
        child_wiki = self.kangaroo_wiki

        url = self.project.api_url_for(
            'project_wiki_delete',
            wname='Koalas'
        )
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.app.delete(
                url,
                auth=self.auth
            )
        self.project.reload()
        parent_wiki.reload()
        assert_equal(parent_wiki.deleted, mock_now)
        child_wiki.reload()
        assert_equal(child_wiki.deleted, mock_now)

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_project_wiki_delete_recursive_two_level(self, mock_shrejs):
        parent_wiki = self.giraffe_wiki
        child_wiki = self.panda_wiki
        grandchild_wiki = self.zebra_wiki

        url = self.project.api_url_for(
            'project_wiki_delete',
            wname='Giraffes'
        )
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.app.delete(
                url,
                auth=self.auth
            )
        self.project.reload()
        parent_wiki.reload()
        assert_equal(parent_wiki.deleted, mock_now)
        child_wiki.reload()
        assert_equal(child_wiki.deleted, mock_now)
        grandchild_wiki.reload()
        assert_equal(grandchild_wiki.deleted, mock_now)

@pytest.mark.enable_implicit_clean
class TestWikiRename(OsfTestCase):

    def setUp(self):
        super(TestWikiRename, self).setUp()

        creator = AuthUserFactory()

        self.project = ProjectFactory(is_public=True, creator=creator)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.auth = creator.auth
        self.wiki = WikiPage.objects.create_for_node(self.project, 'home', 'Hello world', self.consolidate_auth)
        self.page_name = 'page2'
        self.page = WikiPage.objects.create_for_node(self.project, self.page_name, 'content', self.consolidate_auth)
        self.version = self.page.get_version()

        self.url = self.project.api_url_for(
            'project_wiki_rename',
            wname=self.page_name,
        )

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_rename_wiki_page_valid(self, mock_sharejs, new_name=u'away'):
        self.app.put_json(
            self.url,
            {'value': new_name},
            auth=self.auth
        )
        self.project.reload()

        old_wiki =  WikiVersion.objects.get_for_node(self.project, self.page_name)
        assert_false(old_wiki)

        new_wiki =  WikiVersion.objects.get_for_node(self.project, new_name)
        assert_true(new_wiki)
        assert_equal(new_wiki.wiki_page._primary_key, self.page._primary_key)
        assert_equal(new_wiki.content, self.version.content)
        assert_equal(new_wiki.identifier, self.version.identifier)

    def test_rename_wiki_page_invalid(self, new_name=u'invalid/name'):
        res = self.app.put_json(
            self.url,
            {'value': new_name},
            auth=self.auth,
            expect_errors=True,
        )
        assert_equal(http_status.HTTP_400_BAD_REQUEST, res.status_code)
        assert_equal(res.json['message_short'], 'Invalid name')
        assert_equal(res.json['message_long'], 'Page name cannot contain forward slashes.')
        self.project.reload()
        old_wiki = WikiPage.objects.get_for_node(self.project, self.page_name)
        assert_true(old_wiki)

    def test_rename_wiki_page_duplicate(self):
        WikiPage.objects.create_for_node(self.project, 'away', 'Hello world', self.consolidate_auth)
        new_name = 'away'
        res = self.app.put_json(
            self.url,
            {'value': new_name},
            auth=self.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 409)

    def test_rename_wiki_name_not_found(self):
        url = self.project.api_url_for('project_wiki_rename', wname='not_found_page_name')
        res = self.app.put_json(url, {'value': 'new name'},
            auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_cannot_rename_wiki_page_to_home(self):
        user = AuthUserFactory()
        # A fresh project where the 'home' wiki page has no content
        project = ProjectFactory(creator=user)
        WikiPage.objects.create_for_node(project, 'Hello', 'hello world', Auth(user=user))
        url = project.api_url_for('project_wiki_rename', wname='Hello')
        res = self.app.put_json(url, {'value': 'home'}, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_rename_wiki_name_with_value_missing(self):
        # value is missing
        res = self.app.put_json(self.url, {}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_rename_wiki_page_duplicate_different_casing(self):
        # attempt to rename 'page2' from setup to different case of 'away'.
        old_name = 'away'
        new_name = 'AwAy'
        WikiPage.objects.create_for_node(self.project, old_name, 'Hello world', self.consolidate_auth)
        res = self.app.put_json(
            self.url,
            {'value': new_name},
            auth=self.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 409)

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_rename_wiki_page_same_name_different_casing(self, mock_sharejs):
        old_name = 'away'
        new_name = 'AWAY'
        WikiPage.objects.create_for_node(self.project, old_name, 'Hello world', self.consolidate_auth)
        url = self.project.api_url_for('project_wiki_rename', wname=old_name)
        res = self.app.put_json(
            url,
            {'value': new_name},
            auth=self.auth,
            expect_errors=False
        )
        assert_equal(res.status_code, 200)

    def test_cannot_rename_home_page(self):
        url = self.project.api_url_for('project_wiki_rename', wname='home')
        res = self.app.put_json(url, {'value': 'homelol'}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_can_rename_to_a_deleted_page(self, mock_sharejs):
        self.page.delete(self.consolidate_auth)

        # Creates a new page
        WikiPage.objects.create_for_node(self.project, 'page3', 'moarcontent', self.consolidate_auth)

        # Renames the wiki to the deleted page
        url = self.project.api_url_for('project_wiki_rename', wname='page3')
        res = self.app.put_json(url, {'value': self.page_name}, auth=self.auth)
        assert_equal(res.status_code, 200)

    def test_rename_wiki_page_with_valid_html(self):
        # script is not an issue since data is sanitized via bleach or mako before display.
        self.test_rename_wiki_page_valid(new_name=u'<html>hello<html>')

    def test_rename_wiki_page_with_invalid_html(self):
        # script is not an issue since data is sanitized via bleach or mako before display.
        # with that said routes still do not accept forward slashes
        self.test_rename_wiki_page_invalid(new_name=u'<html>hello</html>')

    def test_rename_wiki_page_with_non_ascii_title(self):
        self.test_rename_wiki_page_valid(new_name=u'øˆ∆´ƒøßå√ß')

    def test_rename_wiki_page_with_valid_special_character_title(self):
        self.test_rename_wiki_page_valid(new_name=SPECIAL_CHARACTERS_ALLOWED)

    def test_rename_wiki_page_with_invalid_special_character_title(self):
        self.test_rename_wiki_page_invalid(new_name=SPECIAL_CHARACTERS_ALL)


class TestWikiLinks(OsfTestCase):

    def test_links(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        wiki_page = WikiFactory(
            user=user,
            node=project,
        )
        wiki = WikiVersionFactory(
            content='[[wiki2]]',
            wiki_page=wiki_page,
        )
        assert_in(
            '/{}/wiki/wiki2/'.format(project._id),
            wiki.html(project),
        )

    # Regression test for https://sentry.osf.io/osf/production/group/310/
    def test_bad_links(self):
        content = u'<span></span><iframe src="http://httpbin.org/"></iframe>'
        user = AuthUserFactory()
        node = ProjectFactory()
        wiki_page = WikiFactory(
            user=user,
            node=node,
        )
        wiki = WikiVersionFactory(
            content=content,
            wiki_page=wiki_page,
        )
        expected = render_content(content, node)
        assert_equal(
            '<p><span></span>&lt;iframe src="<a href="http://httpbin.org/" rel="nofollow">http://httpbin.org/</a>"&gt;&lt;/iframe&gt;</p>',
            wiki.html(node)
        )


@pytest.mark.enable_bookmark_creation
class TestWikiUuid(OsfTestCase):

    def setUp(self):
        super(TestWikiUuid, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.wname = 'foo.bar'
        self.wkey = to_mongo_key(self.wname)

    def test_uuid_generated_once(self):
        assert_is_none(self.project.wiki_private_uuids.get(self.wkey))
        url = self.project.web_url_for('project_wiki_view', wname=self.wname)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        self.project.reload()
        private_uuid = self.project.wiki_private_uuids.get(self.wkey)
        assert_true(private_uuid)
        assert_not_in(private_uuid, res.body.decode())
        assert_in(get_sharejs_uuid(self.project, self.wname), res.body.decode())

        # Revisit page; uuid has not changed
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(private_uuid, self.project.wiki_private_uuids.get(self.wkey))

    def test_uuid_not_visible_without_write_permission(self):
        WikiPage.objects.create_for_node(self.project, self.wname, 'some content', Auth(self.user))

        assert_is_none(self.project.wiki_private_uuids.get(self.wkey))
        url = self.project.web_url_for('project_wiki_view', wname=self.wname)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        self.project.reload()
        private_uuid = self.project.wiki_private_uuids.get(self.wkey)
        assert_true(private_uuid)
        assert_not_in(private_uuid, res.body.decode())
        assert_in(get_sharejs_uuid(self.project, self.wname), res.body.decode())

        # Users without write permission should not be able to access
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_not_in(get_sharejs_uuid(self.project, self.wname), res.body.decode())

    def test_uuid_not_generated_without_write_permission(self):
        WikiPage.objects.create_for_node(self.project, self.wname, 'some content', Auth(self.user))

        assert_is_none(self.project.wiki_private_uuids.get(self.wkey))
        url = self.project.web_url_for('project_wiki_view', wname=self.wname)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

        self.project.reload()
        private_uuid = self.project.wiki_private_uuids.get(self.wkey)
        assert_is_none(private_uuid)

    def test_uuids_differ_between_pages(self):
        wname1 = 'foo.bar'
        url1 = self.project.web_url_for('project_wiki_view', wname=wname1)
        res1 = self.app.get(url1, auth=self.user.auth)
        assert_equal(res1.status_code, 200)

        wname2 = 'bar.baz'
        url2 = self.project.web_url_for('project_wiki_view', wname=wname2)
        res2 = self.app.get(url2, auth=self.user.auth)
        assert_equal(res2.status_code, 200)

        self.project.reload()
        uuid1 = get_sharejs_uuid(self.project, wname1)
        uuid2 = get_sharejs_uuid(self.project, wname2)

        assert_not_equal(uuid1, uuid2)
        assert_in(uuid1, res1)
        assert_in(uuid2, res2)
        assert_not_in(uuid1, res2)
        assert_not_in(uuid2, res1)

    def test_uuids_differ_between_forks(self):
        url = self.project.web_url_for('project_wiki_view', wname=self.wname)
        project_res = self.app.get(url, auth=self.user.auth)
        assert_equal(project_res.status_code, 200)
        self.project.reload()

        fork = self.project.fork_node(Auth(self.user))
        assert_true(fork.is_fork_of(self.project))
        fork_url = fork.web_url_for('project_wiki_view', wname=self.wname)
        fork_res = self.app.get(fork_url, auth=self.user.auth)
        assert_equal(fork_res.status_code, 200)
        fork.reload()

        # uuids are not copied over to forks
        assert_not_equal(
            self.project.wiki_private_uuids.get(self.wkey),
            fork.wiki_private_uuids.get(self.wkey)
        )

        project_uuid = get_sharejs_uuid(self.project, self.wname)
        fork_uuid = get_sharejs_uuid(fork, self.wname)

        assert_not_equal(project_uuid, fork_uuid)
        assert_in(project_uuid, project_res)
        assert_in(fork_uuid, fork_res)
        assert_not_in(project_uuid, fork_res)
        assert_not_in(fork_uuid, project_res)

    @pytest.mark.skip('#TODO: Fix or mock mongodb for sharejs')
    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_migration_does_not_affect_forks(self, mock_sharejs):
        original_uuid = generate_private_uuid(self.project, self.wname)
        WikiPage.objects.create_for_node(self.project, self.wname, 'Hello world', Auth(self.user))
        fork = self.project.fork_node(Auth(self.user))
        assert_equal(fork.wiki_private_uuids.get(self.wkey), None)

        migrate_uuid(self.project, self.wname)

        assert_not_equal(original_uuid, self.project.wiki_private_uuids.get(self.wkey))
        assert_equal(fork.wiki_private_uuids.get(self.wkey), None)

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_uuid_persists_after_delete(self, mock_sharejs):
        assert_is_none(self.project.wiki_private_uuids.get(self.wkey))

        # Create wiki page
        WikiPage.objects.create_for_node(self.project, self.wname, 'Hello world', Auth(self.user))

        # Visit wiki edit page
        edit_url = self.project.web_url_for('project_wiki_view', wname=self.wname)
        res = self.app.get(edit_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        original_private_uuid = self.project.wiki_private_uuids.get(self.wkey)
        original_sharejs_uuid = get_sharejs_uuid(self.project, self.wname)

        # Delete wiki
        delete_url = self.project.api_url_for('project_wiki_delete', wname=self.wname)
        res = self.app.delete(delete_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(original_private_uuid, self.project.wiki_private_uuids.get(self.wkey))

        # Revisit wiki edit page
        res = self.app.get(edit_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(original_private_uuid, self.project.wiki_private_uuids.get(self.wkey))
        assert_in(original_sharejs_uuid, res.body.decode())

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_uuid_persists_after_rename(self, mock_sharejs):
        new_wname = 'barbaz'
        new_wkey = to_mongo_key(new_wname)
        assert_is_none(self.project.wiki_private_uuids.get(self.wkey))
        assert_is_none(self.project.wiki_private_uuids.get(new_wkey))

        # Create wiki page
        wiki_page = WikiPage.objects.create_for_node(self.project, self.wname, 'Hello world', Auth(self.user))

        # Visit wiki edit page
        original_edit_url = self.project.web_url_for('project_wiki_view', wname=self.wname)
        res = self.app.get(original_edit_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        original_private_uuid = self.project.wiki_private_uuids.get(self.wkey)
        original_sharejs_uuid = get_sharejs_uuid(self.project, self.wname)

        # Rename wiki
        rename_url = self.project.api_url_for('project_wiki_rename', wname=self.wname)
        res = self.app.put_json(
            rename_url,
            {'value': new_wname, 'pk': wiki_page._id},
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_is_none(self.project.wiki_private_uuids.get(self.wkey))
        assert_equal(original_private_uuid, self.project.wiki_private_uuids.get(new_wkey))

        # Revisit original wiki edit page
        res = self.app.get(original_edit_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_not_equal(original_private_uuid, self.project.wiki_private_uuids.get(self.wkey))
        assert_not_in(original_sharejs_uuid, res.body.decode())


@pytest.mark.skip('#TODO: Fix or mock mongodb for sharejs')
class TestWikiShareJSMongo(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestWikiShareJSMongo, cls).setUpClass()
        cls._original_sharejs_db_name = settings.SHAREJS_DB_NAME
        settings.SHAREJS_DB_NAME = 'sharejs_test'

    def setUp(self):
        super(TestWikiShareJSMongo, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.wname = 'foo.bar'
        self.wkey = to_mongo_key(self.wname)
        self.private_uuid = generate_private_uuid(self.project, self.wname)
        self.sharejs_uuid = get_sharejs_uuid(self.project, self.wname)

        # Create wiki page
        self.wiki_page = WikiPage.objects.create_for_node(self.project, self.wname, 'Hello world', Auth(self.user))

        # Insert mongo data for current project/wiki
        self.db = share_db()
        example_uuid = EXAMPLE_DOCS[0]['_id']
        self.example_docs = deepcopy(EXAMPLE_DOCS)
        self.example_docs[0]['_id'] = self.sharejs_uuid
        self.db.docs.insert(self.example_docs)
        self.example_ops = deepcopy(EXAMPLE_OPS)
        for item in self.example_ops:
            item['_id'] = item['_id'].replace(example_uuid, self.sharejs_uuid)
            item['name'] = item['name'].replace(example_uuid, self.sharejs_uuid)
        self.db.docs_ops.insert(self.example_ops)

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_migrate_uuid(self, mock_sharejs):
        migrate_uuid(self.project, self.wname)
        assert_is_none(self.db.docs.find_one({'_id': self.sharejs_uuid}))
        assert_is_none(self.db.docs_ops.find_one({'name': self.sharejs_uuid}))

        new_sharejs_uuid = get_sharejs_uuid(self.project, self.wname)
        assert_equal(
            EXAMPLE_DOCS[0]['_data'],
            self.db.docs.find_one({'_id': new_sharejs_uuid})['_data']
        )
        assert_equal(
            len([item for item in self.example_ops if item['name'] == self.sharejs_uuid]),
            len([item for item in self.db.docs_ops.find({'name': new_sharejs_uuid})])
        )

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_migrate_uuid_no_mongo(self, mock_sharejs):
        # Case where no edits have been made to the wiki
        wname = 'bar.baz'
        wkey = to_mongo_key(wname)
        share_uuid = generate_private_uuid(self.project, wname)
        sharejs_uuid = get_sharejs_uuid(self.project, wname)

        self.wiki_page.update(self.user, 'Hello world')

        migrate_uuid(self.project, wname)

        assert_not_equal(share_uuid, self.project.wiki_private_uuids.get(wkey))
        assert_is_none(self.db.docs.find_one({'_id': sharejs_uuid}))
        assert_is_none(self.db.docs_ops.find_one({'name': sharejs_uuid}))

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_migrate_uuid_updates_node(self, mock_sharejs):
        migrate_uuid(self.project, self.wname)
        assert_not_equal(self.private_uuid, self.project.wiki_private_uuids[self.wkey])

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_manage_contributors_updates_uuid(self, mock_sharejs):
        user = UserFactory()
        self.project.add_contributor(
            contributor=user,
            permissions=ADMIN,
            auth=Auth(user=self.user),
        )
        self.project.save()
        assert_equal(self.private_uuid, self.project.wiki_private_uuids[self.wkey])
        # Removing admin permission does nothing
        self.project.manage_contributors(
            user_dicts=[
                {'id': user._id, 'permission': WRITE, 'visible': True},
                {'id': self.user._id, 'permission': ADMIN, 'visible': True},
            ],
            auth=Auth(user=self.user),
            save=True,
        )
        assert_equal(self.private_uuid, self.project.wiki_private_uuids[self.wkey])
        # Removing write permission migrates uuid
        self.project.manage_contributors(
            user_dicts=[
                {'id': user._id, 'permission': READ, 'visible': True},
                {'id': self.user._id, 'permission': ADMIN, 'visible': True},
            ],
            auth=Auth(user=self.user),
            save=True,
        )
        assert_not_equal(self.private_uuid, self.project.wiki_private_uuids[self.wkey])

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_delete_share_doc(self, mock_sharejs):
        delete_share_doc(self.project, self.wname)
        assert_is_none(self.db.docs.find_one({'_id': self.sharejs_uuid}))
        assert_is_none(self.db.docs_ops.find_one({'name': self.sharejs_uuid}))

    @mock.patch('addons.wiki.utils.broadcast_to_sharejs')
    def test_delete_share_doc_updates_node(self, mock_sharejs):
        assert_equal(self.private_uuid, self.project.wiki_private_uuids[self.wkey])
        delete_share_doc(self.project, self.wname)
        assert_not_in(self.wkey, self.project.wiki_private_uuids)

    def test_get_draft(self):
        # draft is current with latest wiki save
        current_content = self.wiki_page.get_draft(self.project)
        assert_equals(current_content, self.wiki_page.content)

        # modify the sharejs wiki page contents and ensure we
        # return the draft contents
        new_content = 'I am a teapot'
        new_time = int(time.time() * 1000) + 10000
        new_version = self.example_docs[0]['_v'] + 1
        self.db.docs.update(
            {'_id': self.sharejs_uuid},
            {'$set': {
                '_v': new_version,
                '_m.mtime': new_time,
                '_data': new_content
            }}
        )
        current_content = self.wiki_page.get_draft(self.project)
        assert_equals(current_content, new_content)

    def tearDown(self):
        super(TestWikiShareJSMongo, self).tearDown()
        self.db.drop_collection('docs')
        self.db.drop_collection('docs_ops')

    @classmethod
    def tearDownClass(cls):
        share_db().connection.drop_database(settings.SHAREJS_DB_NAME)
        settings.SHARE_DATABASE_NAME = cls._original_sharejs_db_name


class TestWikiUtils(OsfTestCase):

    def setUp(self):
        super(TestWikiUtils, self).setUp()
        self.project = ProjectFactory()

    def test_get_sharejs_uuid(self):
        wname = 'foo.bar'
        wname2 = 'bar.baz'
        private_uuid = generate_private_uuid(self.project, wname)
        sharejs_uuid = get_sharejs_uuid(self.project, wname)

        # Provides consistent results
        assert_equal(sharejs_uuid, get_sharejs_uuid(self.project, wname))

        # Provides obfuscation
        assert_not_in(wname, sharejs_uuid)
        assert_not_in(sharejs_uuid, wname)
        assert_not_in(private_uuid, sharejs_uuid)
        assert_not_in(sharejs_uuid, private_uuid)

        # Differs based on share uuid provided
        assert_not_equal(sharejs_uuid, get_sharejs_uuid(self.project, wname2))

        # Differs across projects and forks
        project = ProjectFactory()
        assert_not_equal(sharejs_uuid, get_sharejs_uuid(project, wname))
        fork = self.project.fork_node(Auth(self.project.creator))
        assert_not_equal(sharejs_uuid, get_sharejs_uuid(fork, wname))

    def test_generate_share_uuid(self):
        wname = 'bar.baz'
        wkey = to_mongo_key(wname)
        assert_is_none(self.project.wiki_private_uuids.get(wkey))
        share_uuid = generate_private_uuid(self.project, wname)
        self.project.reload()
        assert_equal(self.project.wiki_private_uuids[wkey], share_uuid)

        new_uuid = generate_private_uuid(self.project, wname)
        self.project.reload()
        assert_not_equal(share_uuid, new_uuid)
        assert_equal(self.project.wiki_private_uuids[wkey], new_uuid)

    def test_format_wiki_version(self):
        assert_is_none(format_wiki_version(None, 5, False))
        assert_is_none(format_wiki_version('', 5, False))
        assert_equal(format_wiki_version('3', 5, False), 3)
        assert_equal(format_wiki_version('4', 5, False), 'previous')
        assert_equal(format_wiki_version('5', 5, False), 'current')
        assert_equal(format_wiki_version('previous', 5, False), 'previous')
        assert_equal(format_wiki_version('current', 5, False), 'current')
        assert_equal(format_wiki_version('preview', 5, True), 'preview')
        assert_equal(format_wiki_version('current', 0, False), 'current')
        assert_equal(format_wiki_version('preview', 0, True), 'preview')

        with assert_raises(InvalidVersionError):
            format_wiki_version('1', 0, False)
        with assert_raises(InvalidVersionError):
            format_wiki_version('previous', 0, False)
        with assert_raises(InvalidVersionError):
            format_wiki_version('6', 5, False)
        with assert_raises(InvalidVersionError):
            format_wiki_version('0', 5, False)
        with assert_raises(InvalidVersionError):
            format_wiki_version('preview', 5, False)
        with assert_raises(InvalidVersionError):
            format_wiki_version('nonsense', 5, True)

class TestPublicWiki(OsfTestCase):

    def setUp(self):
        super(TestPublicWiki, self).setUp()
        self.project = ProjectFactory()
        self.consolidate_auth = Auth(user=self.project.creator)
        self.user = AuthUserFactory()

    def test_addon_on_children(self):

        parent = ProjectFactory()
        node = NodeFactory(parent=parent, category='project')
        sub_component = NodeFactory(parent=node)

        parent.delete_addon('wiki', self.consolidate_auth)
        node.delete_addon('wiki', self.consolidate_auth)
        sub_component.delete_addon('wiki', self.consolidate_auth)

        NodeFactory(parent=node)

        has_addon_on_child_node =\
            node.has_addon_on_children('wiki')
        assert_true(has_addon_on_child_node)

    def test_check_user_has_addon_excludes_deleted_components(self):
        parent = ProjectFactory()
        parent.delete_addon('wiki', self.consolidate_auth)
        node = NodeFactory(parent=parent, category='project')
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            node.delete_addon('wiki', self.consolidate_auth)
        sub_component = NodeFactory(parent=node)
        sub_component.is_deleted = True
        sub_component.save()

        has_addon_on_child_node =\
            node.has_addon_on_children('wiki')
        assert_false(has_addon_on_child_node)

    def test_set_editing(self):
        parent = ProjectFactory()
        node = NodeFactory(parent=parent, category='project', is_public=True)
        wiki = node.get_addon('wiki')
        # Set as publicly editable
        wiki.set_editing(permissions=True, auth=self.consolidate_auth, log=True)
        assert_true(wiki.is_publicly_editable)
        assert_equal(node.logs.latest().action, 'made_wiki_public')
        # Try to set public when the wiki is already public
        with assert_raises(NodeStateError):
            wiki.set_editing(permissions=True, auth=self.consolidate_auth, log=False)
        # Turn off public editing
        wiki.set_editing(permissions=False, auth=self.consolidate_auth, log=True)
        assert_false(wiki.is_publicly_editable)
        assert_equal(node.logs.latest().action, 'made_wiki_private')

        node = NodeFactory(parent=parent, category='project')
        wiki = node.get_addon('wiki')

        # Try to set to private wiki already private
        with assert_raises(NodeStateError):
            wiki.set_editing(permissions=False, auth=self.consolidate_auth, log=False)

        # Try to set public when the project is private
        with assert_raises(NodeStateError):
            wiki.set_editing(permissions=True, auth=self.consolidate_auth, log=False)

    def test_serialize_wiki_settings(self):
        node = NodeFactory(parent=self.project, creator=self.user, is_public=True)
        node.get_addon('wiki').set_editing(
            permissions=True, auth=self.consolidate_auth, log=True)
        data = serialize_wiki_settings(self.user, [node])
        expected = [{
            'node': {
                'id': node._id,
                'title': node.title,
                'url': node.url,
            },
            'children': [
                {
                    'select': {
                        'title': 'permission',
                        'permission': 'public'
                    },
                }
            ],
            'kind': 'folder',
            'nodeType': 'component',
            'category': 'hypothesis',
            'permissions': {'view': True}
        }]

        assert_equal(data, expected)

    def test_serialize_wiki_settings(self):
        node = NodeFactory(parent=self.project, creator=self.user, is_public=True)
        node.get_addon('wiki').set_editing(
            permissions=True, auth=self.consolidate_auth, log=True)
        node.save()
        data = serialize_wiki_settings(self.user, [node])
        expected = [{
            'node': {
                'id': node._id,
                'title': node.title,
                'url': node.url,
                'is_public': True
            },
            'children': [
                {
                    'select': {
                        'title': 'permission',
                        'permission': 'public'
                    },
                }
            ],
            'kind': 'folder',
            'nodeType': 'component',
            'category': 'hypothesis',
            'permissions': {'view': True,
                            ADMIN: True}
        }]

        assert_equal(data, expected)

    def test_serialize_wiki_settings_disabled_wiki(self):
        node = NodeFactory(parent=self.project, creator=self.user)
        node.delete_addon('wiki', self.consolidate_auth)
        data = serialize_wiki_settings(self.user, [node])
        expected = [{'node':
                        {'url': node.url,
                         'is_public': False,
                         'id': node._id,
                         'title': node.title},
                    'category': 'hypothesis',
                    'kind': 'folder',
                    'nodeType': 'component',
                    'children': [],
                    'permissions': {ADMIN: True,
                                    'view': True}
                    }]

        assert_equal(data, expected)

@pytest.mark.enable_bookmark_creation
class TestWikiMenu(OsfTestCase):

    def setUp(self):
        super(TestWikiMenu, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=True)
        self.component = NodeFactory(creator=self.user, parent=self.project, is_public=True)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.non_contributor = UserFactory()

    def test_format_home_wiki_page_no_content(self):
        data = views.format_home_wiki_page(self.project)
        expected = {
            'page': {
                'url': self.project.web_url_for('project_wiki_home'),
                'name': 'Home',
                'id': 'None',
            }
        }
        assert_equal(data, expected)

    def test_format_project_wiki_pages_contributor(self):
        home_page = WikiPage.objects.create_for_node(self.project, 'home', 'content here', self.consolidate_auth)
        zoo_page = WikiPage.objects.create_for_node(self.project, 'zoo', 'koala', self.consolidate_auth)
        data = views.format_project_wiki_pages(self.project, self.consolidate_auth)
        expected = [
            {
                'page': {
                    'url': self.project.web_url_for('project_wiki_view', wname='home', _guid=True),
                    'name': 'Home',
                    'id': home_page._primary_key,
                }
            },
            {
                'page': {
                    'url': self.project.web_url_for('project_wiki_view', wname='zoo', _guid=True),
                    'name': 'zoo',
                    'sort_order': None,
                    'id': zoo_page._primary_key,
                },
                'children': [],
            }
        ]
        assert_equal(data, expected)

    def test_format_project_wiki_pages_no_content_non_contributor(self):
        home_page = WikiPage.objects.create_for_node(self.project, 'home', 'content here', self.consolidate_auth)
        zoo_page = WikiPage.objects.create_for_node(self.project, 'zoo', '', self.consolidate_auth)
        home_page = WikiVersion.objects.get_for_node(self.project, 'home')
        data = views.format_project_wiki_pages(self.project, auth=Auth(self.non_contributor))
        expected = [
            {
                'page': {
                    'url': self.project.web_url_for('project_wiki_view', wname='home', _guid=True),
                    'name': 'Home',
                    'id': home_page.wiki_page._primary_key,
                }
            }
        ]
        assert_equal(data, expected)

    def test_format_project_default_home_has_child(self):
        self.home_wiki = WikiPage.objects.create_for_node(self.project, 'home', 'home content', self.consolidate_auth)
        self.home_child_wiki = WikiPage.objects.create_for_node(self.project, 'home child', 'home child content', self.consolidate_auth, self.home_wiki)
        project_format = views.format_project_wiki_pages(node=self.project, auth=self.consolidate_auth)
        result_home_kind = project_format[0]['kind']
        result_home_child = project_format[0]['children']
        guid = self.project.guids.first()._id
        expected_home_child_result = [
            {
                'page': {
                    'url': f'/{guid}/wiki/home%20child/',
                    'name': 'home child',
                    'id': self.home_child_wiki._primary_key,
                    'sort_order': None
                    },
                'children': []
            }
        ]
        assert_equal(result_home_kind, 'folder')
        assert_equal(result_home_child, expected_home_child_result)

    def test_format_project_default_home_has_grandchild(self):
        self.home_wiki = WikiPage.objects.create_for_node(self.project, 'home', 'home content', self.consolidate_auth)
        self.home_child_wiki = WikiPage.objects.create_for_node(self.project, 'home child', 'home child content', self.consolidate_auth, self.home_wiki)
        self.home_grandchild_wiki = WikiPage.objects.create_for_node(self.project, 'home grandchild', 'home grandchild content', self.consolidate_auth, self.home_child_wiki)
        project_format = views.format_project_wiki_pages(node=self.project, auth=self.consolidate_auth)
        result_home_child_kind = project_format[0]['children'][0]['kind']
        result_home_grandchild = project_format[0]['children'][0]['children']
        guid = self.project.guids.first()._id
        expected_home_grandchild_result = [
            {
                'page': {
                    'url': f'/{guid}/wiki/home%20grandchild/',
                    'name': 'home grandchild',
                    'id': self.home_grandchild_wiki._primary_key,
                    'sort_order': None
                    },
                'children': []
            }
        ]
        assert_equal(result_home_child_kind, 'folder')
        assert_equal(result_home_grandchild, expected_home_grandchild_result)

    def test_format_project_has_child(self):
        self.parent_wiki_page = WikiPage.objects.create_for_node(self.project, 'parent page', 'parent content', self.consolidate_auth)
        self.child_wiki_page = WikiPage.objects.create_for_node(self.project, 'child page', 'child content', self.consolidate_auth, self.parent_wiki_page)
        project_format = views.format_project_wiki_pages(node=self.project, auth=self.consolidate_auth)
        result_parent_kind = project_format[1]['kind']
        result_child = project_format[1]['children']
        guid = self.project.guids.first()._id
        expected_child_result = [
            {
                'page': {
                'url': f'/{guid}/wiki/child%20page/',
                'name': 'child page',
                'id': self.child_wiki_page._primary_key,
                "sort_order": None
                },
                "children": []
            }
        ]
        assert_equal(result_parent_kind, 'folder')
        assert_equal(result_child, expected_child_result)

    def test_format_project_has_grandchild(self):
        self.parent_wiki_page = WikiPage.objects.create_for_node(self.project, 'parent page', 'parent content', self.consolidate_auth)
        self.child_wiki_page = WikiPage.objects.create_for_node(self.project, 'child page', 'child content', self.consolidate_auth, self.parent_wiki_page)
        self.grandchild_wiki_page = WikiPage.objects.create_for_node(self.project, 'grandchild page', 'grandchild content', self.consolidate_auth, self.child_wiki_page)
        project_format = views.format_project_wiki_pages(node=self.project, auth=self.consolidate_auth)
        result_child_kind = project_format[1]['children'][0]['kind']
        result_grandchild = project_format[1]['children'][0]['children']
        guid = self.project.guids.first()._id
        expected_grandchild_result = [
            {
                'page': {
                    'url': f'/{guid}/wiki/grandchild%20page/',
                    'name': 'grandchild page',
                    'id': self.grandchild_wiki_page._primary_key,
                    'sort_order': None
                },
                "children": []
            }
        ]
        assert_equal(result_child_kind, 'folder')
        assert_equal(result_grandchild, expected_grandchild_result)


    def test_format_component_wiki_pages_contributor(self):
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

    def test_format_component_wiki_pages_no_content_non_contributor(self):
        data = views.format_component_wiki_pages(node=self.project, auth=Auth(self.non_contributor))
        expected = []
        assert_equal(data, expected)

    def test_format_component_default_home_has_child(self):
        self.home_wiki = WikiPage.objects.create_for_node(self.component, 'home', 'home content', self.consolidate_auth)
        self.home_child_wiki = WikiPage.objects.create_for_node(self.component, 'home child', 'home child content', self.consolidate_auth, self.home_wiki)
        component_format = views.format_component_wiki_pages(node=self.project, auth=self.consolidate_auth)
        result_home_kind = component_format[0]['children'][0]['kind']
        result_home_child = component_format[0]['children'][0]['children']
        guid = self.component.guids.first()._id
        expected_home_child_result = [
            {
                'page': {
                    'url': f'/{guid}/wiki/home%20child/',
                    'name': 'home child',
                    'id': self.home_child_wiki._primary_key,
                    'sort_order': None
                    },
                'children': []
            }
        ]
        assert_equal(result_home_kind, 'folder')
        assert_equal(result_home_child, expected_home_child_result)

    def test_format_component_default_home_has_grandchild(self):
        self.home_wiki = WikiPage.objects.create_for_node(self.component, 'home', 'home content', self.consolidate_auth)
        self.home_child_wiki = WikiPage.objects.create_for_node(self.component, 'home child', 'home child content', self.consolidate_auth, self.home_wiki)
        self.home_grandchild_wiki = WikiPage.objects.create_for_node(self.component, 'home grandchild', 'home grandchild content', self.consolidate_auth, self.home_child_wiki)
        component_format = views.format_component_wiki_pages(node=self.project, auth=self.consolidate_auth)
        result_home_child_kind = component_format[0]['children'][0]['children'][0]['kind']
        result_home_grandchild = component_format[0]['children'][0]['children'][0]['children']
        guid = self.component.guids.first()._id
        expected_home_grandchild_result = [
            {
                'page': {
                    'url': f'/{guid}/wiki/home%20grandchild/',
                    'name': 'home grandchild',
                    'id': self.home_grandchild_wiki._primary_key,
                    'sort_order': None
                    },
                'children': []
            }
        ]
        assert_equal(result_home_child_kind, 'folder')
        assert_equal(result_home_grandchild, expected_home_grandchild_result)

    def test_format_component_has_child(self):
        self.parent_wiki_page = WikiPage.objects.create_for_node(self.component, 'parent page', 'parent content', self.consolidate_auth)
        self.child_wiki_page = WikiPage.objects.create_for_node(self.component, 'child page', 'child content', self.consolidate_auth, self.parent_wiki_page)
        component_format = views.format_component_wiki_pages(node=self.project, auth=self.consolidate_auth)
        result_parent_kind = component_format[0]['children'][1]['kind']
        result_child = component_format[0]['children'][1]['children']
        guid = self.component.guids.first()._id
        expected_child_result = [
            {
                'page': {
                'url': f'/{guid}/wiki/child%20page/',
                'name': 'child page',
                'id': self.child_wiki_page._primary_key,
                "sort_order": None
                },
                "children": []
            }
        ]
        assert_equal(result_parent_kind, 'folder')
        assert_equal(result_child, expected_child_result)

    def test_format_component_has_grandchild(self):
        self.parent_wiki_page = WikiPage.objects.create_for_node(self.component, 'parent page', 'parent content', self.consolidate_auth)
        self.child_wiki_page = WikiPage.objects.create_for_node(self.component, 'child page', 'child content', self.consolidate_auth, self.parent_wiki_page)
        self.grandchild_wiki_page = WikiPage.objects.create_for_node(self.component, 'grandchild page', 'grandchild content', self.consolidate_auth, self.child_wiki_page)
        component_format = views.format_component_wiki_pages(node=self.project, auth=self.consolidate_auth)
        result_child_kind = component_format[0]['children'][1]['children'][0]['kind']
        result_grandchild = component_format[0]['children'][1]['children'][0]['children']
        guid = self.component.guids.first()._id
        expected_grandchild_result = [
            {
                'page': {
                    'url': f'/{guid}/wiki/grandchild%20page/',
                    'name': 'grandchild page',
                    'id': self.grandchild_wiki_page._primary_key,
                    'sort_order': None
                },
                "children": []
            }
        ]
        assert_equal(result_child_kind, 'folder')
        assert_equal(result_grandchild, expected_grandchild_result)

    def test_project_wiki_grid_data(self):
        WikiPage.objects.create_for_node(self.project, 'home', 'project content', self.consolidate_auth)
        WikiPage.objects.create_for_node(self.component, 'home', 'component content', self.consolidate_auth)
        data = views.project_wiki_grid_data(auth=self.consolidate_auth, wname='home', node=self.project)
        expected = [
            {
                'title': 'Project Wiki Pages',
                'kind': 'folder',
                'type': 'heading',
                'children': views.format_project_wiki_pages(node=self.project, auth=self.consolidate_auth),
            },
            {
                'title': 'Component Wiki Pages',
                'kind': 'folder',
                'type': 'heading',
                'children': views.format_component_wiki_pages(node=self.project, auth=self.consolidate_auth)
            }
        ]
        assert_equal(data, expected)

    def test_project_wiki_grid_data_has_child(self):
        WikiPage.objects.create_for_node(self.project, 'home', 'project content', self.consolidate_auth)
        project_parent_wiki = WikiPage.objects.create_for_node(self.project, 'parent', 'project content', self.consolidate_auth)
        WikiPage.objects.create_for_node(self.project, 'child', 'project content', self.consolidate_auth, project_parent_wiki)
        component_parent_wiki = WikiPage.objects.create_for_node(self.component, 'home', 'component content', self.consolidate_auth)
        WikiPage.objects.create_for_node(self.component, 'parent', 'component content', self.consolidate_auth, component_parent_wiki)
        data = views.project_wiki_grid_data(auth=self.consolidate_auth, wname='home', node=self.project)
        expected = [
            {
                'title': 'Project Wiki Pages',
                'kind': 'folder',
                'type': 'heading',
                'children': views.format_project_wiki_pages(node=self.project, auth=self.consolidate_auth),
            },
            {
                'title': 'Component Wiki Pages',
                'kind': 'folder',
                'type': 'heading',
                'children': views.format_component_wiki_pages(node=self.project, auth=self.consolidate_auth)
            }
        ]
        assert_equal(data, expected)

class TestWikiImport(OsfTestCase):

    def setUp(self):
        super(TestWikiImport, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.root = BaseFileNode.objects.get(target_object_id=self.project.id, is_root=True)
        self.consolidate_auth = Auth(user=self.project.creator)

        # importpage1
        self.root_import_folder1 = TestFolder.objects.create(name='rootimportfolder1', target=self.project, parent=self.root)
        self.import_page_folder1 = TestFolder.objects.create(name='importpage1', target=self.project, parent=self.root_import_folder1)
        self.import_page_md_file1 = TestFile.objects.create(name='importpage1.md', target=self.project, parent=self.import_page_folder1)

        # importpagea - importpagec
        # importpageb(pdf)
        self.root_import_folder_a = TestFolder.objects.create(name='rootimportfoldera', target=self.project, parent=self.root)
        self.import_page_folder_a = TestFolder.objects.create(name='importpagea', target=self.project, parent=self.root_import_folder_a)
        self.import_page_md_file_a = TestFile.objects.create(name='importpagea.md', target=self.project, parent=self.import_page_folder_a)
        self.import_page_folder_b = TestFolder.objects.create(name='importpageb', target=self.project, parent=self.root_import_folder_a)
        self.import_page_md_file_b = TestFile.objects.create(name='importpageb.md', target=self.project, parent=self.import_page_folder_b)
        self.import_page_pdf_file = TestFile.objects.create(name='pdffile.pdf', target=self.project, parent=self.import_page_folder_b)
        self.import_page_folder_c = TestFolder.objects.create(name='importpagec', target=self.project, parent=self.root_import_folder_a)
        self.import_page_md_file_c = TestFile.objects.create(name='importpagec.md', target=self.project, parent=self.import_page_folder_c)

        # existing wiki page in project1
        self.wiki_page1 = WikiPage.objects.create_for_node(self.project, 'importpagea', 'wiki pagea content', self.consolidate_auth)
        self.wiki_page2 = WikiPage.objects.create_for_node(self.project, 'importpageb', 'wiki pageb content', self.consolidate_auth)
    
        # importpagex
        self.root_import_folder_x = TestFolder.objects.create(name='rootimportfolderx', target=self.project, parent=self.root)
        self.import_page_folder_invalid = TestFolder.objects.create(name='importpagex', target=self.project, parent=self.root_import_folder_x)

        self.project2 = ProjectFactory(is_public=True, creator=self.user)
        self.root2 = BaseFileNode.objects.get(target_object_id=self.project2.id, is_root=True)
        self.consolidate_auth2 = Auth(user=self.project2.creator)

        # existing wiki page in project2
        self.wiki_page3 = WikiPage.objects.create_for_node(self.project2, 'importpagec', 'wiki pagec content', self.consolidate_auth2)
        self.wiki_page4 = WikiPage.objects.create_for_node(self.project2, 'importpaged', 'wiki paged content', self.consolidate_auth2, self.wiki_page3)

        # importpage1(doc) - importpage2(pdf)
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

    @mock.patch('addons.wiki.utils.check_file_object_in_node')
    def test_project_wiki_validate_for_import_error(self, mock_check_file_object_in_node):
        mock_check_file_object_in_node.side_effect = HTTPError(400, data=dict(
            message_short='directory id does not exist',
            message_long='directory id does not exist'
        ))
        dir_id = self.root_import_folder1._id
        url = self.project.api_url_for('project_wiki_validate_for_import', dir_id=dir_id)
        res = self.app.get(url, expect_errors=True)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json['message_short'], 'directory id does not exist')
        self.assertEqual(res.json['message_long'], 'directory id does not exist')

    def test_validate_import_duplicated_directry_no_duplicated(self):
        info_list = []
        result = views._validate_import_duplicated_directry(info_list)
        self.assertEqual(result, [])

    def test_validate_import_duplicated_directry_duplicated(self):
        info_list = [
            {'original_name': 'folder1'},
            {'original_name': 'folder2'},
            {'original_name': 'folder1'},
            {'original_name': 'folder3'}
        ]
        result = views._validate_import_duplicated_directry(info_list)
        self.assertEqual(result, ['folder1'])

    def test_validate_import_wiki_exists_duplicated_valid_exists_status_change(self):
        info = {'wiki_name': 'importpagea', 'path': '/importpagea', 'status': 'valid'}
        result, can_start_import = views._validate_import_wiki_exists_duplicated(self.project, info)
        self.assertEqual(result['status'], 'valid_exists')
        self.assertFalse(can_start_import)

    def test_validate_import_wiki_exists_duplicated_valid_duplicated_status_change(self):
        info = {'wiki_name': 'importpageb', 'path': '/importpagea/importpageb', 'status': 'valid'}
        result, can_start_import = views._validate_import_wiki_exists_duplicated(self.project, info)
        self.assertEqual(result['status'], 'valid_duplicated')
        self.assertFalse(can_start_import)

    def test_validate_import_wiki_exists_duplicated_valid_no_change(self):
        info = {'wiki_name': 'importpagec', 'path': '/importpagea/importpagec', 'status': 'valid'}
        result, can_start_import = views._validate_import_wiki_exists_duplicated(self.project, info)
        self.assertEqual(result['status'], 'valid')
        self.assertTrue(can_start_import)

    def test_validate_import_folder_invalid(self):
        folder = BaseFileNode.objects.get(name='importpagex')
        parent_path = ''
        result = views._validate_import_folder(self.project, folder, parent_path)
        for info in result:
            self.assertEqual(info['path'], '/importpagex')
            self.assertEqual(info['original_name'], 'importpagex')
            self.assertEqual(info['name'], 'importpagex')
            self.assertEqual(info['status'], 'invalid')
            self.assertEqual(info['message'], 'The wiki page does not exist, so the subordinate pages are not processed.')

    def test_validate_import_folder(self):
        folder = self.import_page_folder_1
        parent_path = ''
        result = views._validate_import_folder(self.project, folder, parent_path)
        expected_results = [
            {'parent_wiki_name': 'importpage1', 'path': '/importpage1/importpage2', 'original_name': 'importpage2', 'wiki_name': 'importpage2', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_2._id},
            {'parent_wiki_name': None, 'path': '/importpage1', 'original_name': 'importpage1', 'wiki_name': 'importpage1', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_1._id}
        ]
        for expected_result in expected_results:
            self.assertIn(expected_result, result)

    def test_project_wiki_validate_for_import_process(self):
        result = views.project_wiki_validate_for_import_process(self.root_import_folder_validate._id, self.project)
        self.assertEqual(result['duplicated_folder'], [])
        self.assertTrue(result['canStartImport'])
        self.assertEqual(result['data'], [{'parent_wiki_name': 'importpage1', 'path': '/importpage1/importpage2', 'original_name': 'importpage2', 'wiki_name': 'importpage2', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_2._id}, {'parent_wiki_name': None, 'path': '/importpage1', 'original_name': 'importpage1', 'wiki_name': 'importpage1', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_1._id}])
    # bag fix
    def test_project_wiki_validate_for_import_process_invalid(self):
        root_import_folder = OsfStorageFolder(name='rootimportfolder', target=self.project, parent=self.root)
        root_import_folder.save()
        import_invalid = OsfStorageFile(name='invalidfile', target=self.project, parent=root_import_folder)
        import_invalid.save()
        import_page_folder = OsfStorageFolder(name='importpage', target=self.project, parent=root_import_folder)
        import_page_folder.save()
        import_page_md_file = OsfStorageFile(name='importpage.md', target=self.project, parent=import_page_folder)
        import_page_md_file.save()
        result = views.project_wiki_validate_for_import_process(root_import_folder._id, self.project)
        self.assertEqual(result['duplicated_folder'], [])
        self.assertTrue(result['canStartImport'])
        expected_results = [
            {'parent_wiki_name': None, 'path': '/importpage', 'original_name': 'importpage', 'wiki_name': 'importpage', 'status': 'valid', 'message': '', '_id': import_page_md_file._id},
            {'path': 'rootimportfolder', 'original_name': 'invalidfile', 'name': 'invalidfile', 'status': 'invalid', 'message': 'This file cannot be imported.', 'parent_name': None}
        ]
        for expected_result in expected_results:
            self.assertIn(expected_result, result['data'])

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

    @mock.patch('addons.wiki.utils.check_file_object_in_node')
    def test_project_wiki_import_error(self, mock_check_file_object_in_node):
        mock_check_file_object_in_node.side_effect = HTTPError(400, data=dict(
            message_short='directory id does not exist',
            message_long='directory id does not exist'
        ))
        dir_id = self.root_import_folder1._id
        url = self.project.api_url_for('project_wiki_import', dir_id=dir_id)
        res = self.app.post_json(url, { 'data': [{'test': 'test1'}] }, auth=self.user.auth, expect_errors=True)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json['message_short'], 'directory id does not exist')
        self.assertEqual(res.json['message_long'], 'directory id does not exist')

    def test_project_wiki_import_with_no_admin_permission(self):
        url = self.project.api_url_for('project_wiki_import', dir_id='dir_id')
        res = self.app.post_json(url, { 'data': [{'test': 'test1'}] }, expect_errors=True)
        assert_equal(res.status_code, 401)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_aborted(self, mock_task):
        mock_task.is_aborted.return_value = True
        expected_content = 'wiki paged content'
        with self.assertRaises(ImportTaskAbortedError):
            views._wiki_import_create_or_update('/importpagec/importpaged', 'wiki paged content', self.consolidate_auth ,self.project2, mock_task, 'importpagec')

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_update_not_changed(self, mock_task):
        mock_task.is_aborted.return_value = False
        expected_content = 'wiki paged content'
        result, updated_wiki_id = views._wiki_import_create_or_update('/importpagec/importpaged', 'wiki paged content', self.consolidate_auth ,self.project2, mock_task, 'importpagec')
        self.assertEqual(result, {'status': 'unmodified', 'path': '/importpagec/importpaged'})
        self.assertIsNone(updated_wiki_id)
        new_wiki_version = WikiVersion.objects.get_for_node(self.project2, 'importpaged')
        self.assertEqual(new_wiki_version.content, 'wiki paged content')

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_update_changed(self, mock_task):
        mock_task.is_aborted.return_value = False
        expected_content = 'new wiki paged content'
        result, updated_wiki_id = views._wiki_import_create_or_update('/importpagec/importpaged', 'new wiki paged content', self.consolidate_auth ,self.project2, mock_task, 'importpagec')
        self.assertEqual(result, {'status': 'success', 'path': '/importpagec/importpaged'})
        self.assertEqual(self.wiki_page4.id, updated_wiki_id)
        new_wiki_version = WikiVersion.objects.get_for_node(self.project2, 'importpaged')
        self.assertEqual(new_wiki_version.content, expected_content)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_create_home(self, mock_task):
        mock_task.is_aborted.return_value = False
        expected_content = 'home wiki page content'
        result, updated_wiki_id = views._wiki_import_create_or_update('/HOME', 'home wiki page content', self.consolidate_auth ,self.project2, mock_task)
        self.assertEqual(result, {'status': 'success', 'path': '/HOME'})
        new_wiki_version = WikiVersion.objects.get_for_node(self.project2, 'home')
        self.assertEqual(new_wiki_version.wiki_page.id, updated_wiki_id)
        self.assertEqual(new_wiki_version.content, expected_content)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_create(self, mock_task):
        mock_task.is_aborted.return_value = False
        expected_content = 'wiki page content'
        result, updated_wiki_id = views._wiki_import_create_or_update('/wikipagename', 'wiki page content', self.consolidate_auth ,self.project2, mock_task)
        self.assertEqual(result, {'status': 'success', 'path': '/wikipagename'})
        new_wiki_version = WikiVersion.objects.get_for_node(self.project2, 'wikipagename')
        self.assertEqual(new_wiki_version.wiki_page.id, updated_wiki_id)
        self.assertEqual(new_wiki_version.content, expected_content)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_update_changed_nfd(self, mock_task):
        mock_task.is_aborted.return_value = False
        path_nfd = unicodedata.normalize('NFD', '/importpagec/importpaged')
        content_nfd = unicodedata.normalize('NFD', 'new wiki paged content')
        parent_name_nfd = unicodedata.normalize('NFD', 'importpagec')
        expected_content = 'new wiki paged content'
        result, updated_wiki_id = views._wiki_import_create_or_update(path_nfd, content_nfd, self.consolidate_auth ,self.project2, mock_task, parent_name_nfd)
        self.assertEqual(result, {'status': 'success', 'path': '/importpagec/importpaged'})
        self.assertEqual(self.wiki_page4.id, updated_wiki_id)
        new_wiki_version = WikiVersion.objects.get_for_node(self.project2, 'importpaged')
        self.assertEqual(new_wiki_version.content, expected_content)

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_wiki_import_create_or_update_does_not_exist_parent(self, mock_task):
        mock_task.is_aborted.return_value = False
        expected_content = 'wiki page content'
        with self.assertRaises(Exception) as cm:
            views._wiki_import_create_or_update('/wikipagename', 'wiki page content', self.consolidate_auth ,self.project2, mock_task, 'notexisitparentwiki')

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    @mock.patch('addons.wiki.views._wiki_import_create_or_update')
    @mock.patch('addons.wiki.views._import_same_level_wiki')
    @mock.patch('addons.wiki.tasks.run_update_search_and_bulk_index')
    def test_project_wiki_import_process(self, mock_run_task_elasticsearch, mock_import_same_level_wiki, mock_wiki_import_create_or_update, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        self.import_page_folder_1 = TestFolder.objects.create(name='importpage1', target=self.project, parent=self.root_import_folder)
        self.import_page_md_file_1 = TestFile.objects.create(name='importpage1.md', target=self.project, parent=self.import_page_folder_1)
        self.import_page_folder_2 = TestFolder.objects.create(name='importpage2', target=self.project, parent=self.import_page_folder_1)
        self.import_page_md_file_2 = TestFile.objects.create(name='importpage2.md', target=self.project, parent=self.import_page_folder_2)
        self.import_page_folder_3 = TestFolder.objects.create(name='importpage3', target=self.project, parent=self.import_page_folder_2)
        self.import_page_md_file_3 = TestFile.objects.create(name='importpage3.md', target=self.project, parent=self.import_page_folder_3)
        self.import_page_folder_4 = TestFolder.objects.create(name='importpage4', target=self.project, parent=self.root_import_folder)
        self.import_page_md_file_4 = TestFile.objects.create(name='importpage4.md', target=self.project, parent=self.import_page_folder_4)
        self.import_page_folder_5 = TestFolder.objects.create(name='importpage5', target=self.project, parent=self.import_page_folder_4)
        self.import_page_md_file_5 = TestFile.objects.create(name='importpage5.md', target=self.project, parent=self.import_page_folder_5)
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
        self.assertEqual(result, expected_result)
        mock_run_task_elasticsearch.delay.assert_called_once_with(self.project.guids.first()._id, [4, 1, 5, 2, 3])
        task = WikiImportTask.objects.get(task_id='task_id')
        self.assertEqual(task.status, task.STATUS_COMPLETED)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    @mock.patch('addons.wiki.views._wiki_import_create_or_update')
    @mock.patch('addons.wiki.tasks.run_update_search_and_bulk_index')
    @mock.patch('addons.wiki.views.set_wiki_import_task_proces_end')
    def test_project_wiki_import_process_top_level_aborted(self, mock_wiki_import_task_prcess_end, mock_run_task_elasticsearch, mock_wiki_import_create_or_update, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
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
        self.assertEqual(result, expected_result)
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
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
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
        self.assertEqual(result, expected_result)
        mock_run_task_elasticsearch.delay.assert_called_once_with(self.project.guids.first()._id, [4, 1])
        mock_wiki_import_task_prcess_end.assert_called_once_with(self.project)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    def test_project_wiki_import_process_wb_aborted(self, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        mock_get_md_content_from_wb.return_value = None
        expected_result = {'aborted': True}
        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        self.assertEqual(result, expected_result)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    def test_project_wiki_import_process_replace_aborted(self, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
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
        self.assertEqual(result, expected_result)

class TestWikiCreatFolderAndCopy(OsfTestCase):

    def setUp(self):
        super(TestWikiCreatFolderAndCopy, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.root = BaseFileNode.objects.get(target_object_id=self.project.id, is_root=True)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.copy_to_dir = TestFolder.objects.create(name='copytodir', target=self.project, parent=self.root)
        self.root_import_folder1 = TestFolder.objects.create(name='rootimportfolder1', target=self.project, parent=self.root)
        self.import_page_folder1 = TestFolder.objects.create(name='importpage1', target=self.project, parent=self.root_import_folder1)
        self.import_page_folder2 = TestFolder.objects.create(name='importpage2', target=self.project, parent=self.root_import_folder1)
        self.import_page_md_file1 = TestFile.objects.create(name='importpage1.md', target=self.project, parent=self.import_page_folder1)
        self.import_page_md_file2 = TestFile.objects.create(name='importpage2.md', target=self.project, parent=self.import_page_folder2)
        self.import_attachment_image1 = TestFile.objects.create(name='image1.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment_image2 = TestFile.objects.create(name='image2.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment_image3 = TestFile.objects.create(name='ima/ge3.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment1_doc = TestFile.objects.create(name='attachment1.doc', target=self.project, parent=self.import_page_folder1)
        self.import_attachment2_txt = TestFile.objects.create(name='wiki#page.txt', target=self.project, parent=self.import_page_folder1)
        self.import_attachment3_xlsx = TestFile.objects.create(name='attachment3.xlsx', target=self.project, parent=self.import_page_folder2)
        self.guid = self.project.guids.first()._id
        self.osf_cookie = self.user.get_or_create_cookie().decode()

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
        self.assertEqual(folder_id, 1)
        self.assertEqual(folder_path, 'osfstorage/aabbcc/')

    @mock.patch('addons.wiki.views._create_wiki_folder')
    def test_get_or_create_wiki_folder_create(self, mock_create_wiki_folder):
        mock_create_wiki_folder.return_value = (1, 'osfstorage/xxyyzz/')
        osf_cookie = self.osf_cookie
        creator, creator_auth = get_creator_auth_header(self.user)
        p_guid = self.guid
        folder_id, folder_path = views._get_or_create_wiki_folder(osf_cookie, self.project, self.root.id, self.user, creator_auth, 'Wiki images', parent_path='osfstorage/')
        self.assertEqual(folder_id, 1)
        self.assertEqual(folder_path, 'osfstorage/xxyyzz/')

    @mock.patch('website.util.waterbutler.create_folder')
    @mock.patch('addons.wiki.views.BaseFileNode')
    def test_create_wiki_folder_success(self, mock_base_file_node, mock_create_folder):
        mock_response = {
            'data': {
                'id': 'osfstorage/xxyyzz/',
                'attributes': {
                    'path': '/xxyyzz/'
                }
            }
        }
        mock_create_folder.return_value = MockResponse(mock_response, 200)
        mock_base_file_node_instance = mock.Mock()
        mock_base_file_node_instance.id = 1
        mock_base_file_node.objects.get.return_value = mock_base_file_node_instance

        osf_cookie = self.osf_cookie
        p_guid = self.guid
        folder_name = 'Wiki images'
        parent_path = 'osfstorage/'
        folder_id, folder_path = views._create_wiki_folder(osf_cookie, p_guid, folder_name, parent_path)

        expected_folder_id = 1
        expected_folder_path = 'osfstorage/xxyyzz/'

        self.assertEqual(folder_id, expected_folder_id)
        self.assertEqual(folder_path, expected_folder_path)

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
            self.assertEqual('Error when create wiki folder', e.data['message_short'])
            self.assertIn('An error occures when create wiki folder', e.data['message_long'])

    @mock.patch('website.files.utils.copy_files')
    @mock.patch('addons.wiki.views.BaseFileNode')
    def test_wiki_copy_import_directory(self, mock_base_file_node, mock_copy_files):
        mock_base_file_node_instance = mock.Mock()
        mock_base_file_node_instance._id = 'ddeeff'
        mock_copy_files.return_value = mock_base_file_node_instance
        cloned_id = views._wiki_copy_import_directory(self.copy_to_dir._id, self.root_import_folder1._id, self.project)
        self.assertEqual(cloned_id, 'ddeeff')

class TestWikiImportReplace(OsfTestCase):

    def setUp(self):
        super(TestWikiImportReplace, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.root = BaseFileNode.objects.get(target_object_id=self.project.id, is_root=True)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.root_import_folder1 = TestFolder.objects.create(name='rootimportfolder1', target=self.project, parent=self.root)
        self.import_page_folder1 = TestFolder.objects.create(name='importpage1', target=self.project, parent=self.root_import_folder1)
        self.import_page_folder2 = TestFolder.objects.create(name='importpage2', target=self.project, parent=self.root_import_folder1)
        self.import_page_md_file1 = TestFile.objects.create(name='importpage1.md', target=self.project, parent=self.import_page_folder1)
        self.import_page_md_file2 = TestFile.objects.create(name='importpage2.md', target=self.project, parent=self.import_page_folder2)
        self.import_attachment_image1 = TestFile.objects.create(name='image1.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment_image2 = TestFile.objects.create(name='image2.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment_image3 = TestFile.objects.create(name='ima/ge3.png', target=self.project, parent=self.import_page_folder1)
        self.import_attachment1_doc = TestFile.objects.create(name='attachment1.doc', target=self.project, parent=self.import_page_folder1)
        self.import_attachment2_txt = TestFile.objects.create(name='wiki#page.txt', target=self.project, parent=self.import_page_folder1)
        self.import_attachment3_xlsx = TestFile.objects.create(name='attachment3.xlsx', target=self.project, parent=self.import_page_folder2)
        self.wiki_info = {'original_name': 'importpage1'}
        self.node_file_mapping = [
            { 'wiki_file': f'{self.import_page_folder1.name}^{self.import_page_md_file1.name}', 'file_id': self.import_page_md_file1._id },
            { 'wiki_file': f'{self.import_page_folder2.name}^{self.import_page_md_file2.name}', 'file_id': self.import_page_md_file2._id },
            { 'wiki_file': f'{self.import_page_folder1.name}^{self.import_attachment_image1.name}', 'file_id': self.import_attachment_image1._id },
            { 'wiki_file': f'{self.import_page_folder1.name}^{self.import_attachment_image2.name}', 'file_id': self.import_attachment_image2._id },
            { 'wiki_file': f'{self.import_page_folder1.name}^{self.import_attachment_image3.name}', 'file_id': self.import_attachment_image3._id },
            { 'wiki_file': f'{self.import_page_folder1.name}^{self.import_attachment1_doc.name}', 'file_id': self.import_attachment1_doc._id },
            { 'wiki_file': f'{self.import_page_folder1.name}^{self.import_attachment2_txt.name}', 'file_id': self.import_attachment2_txt._id },
            { 'wiki_file': f'{self.import_page_folder2.name}^{self.import_attachment3_xlsx.name}', 'file_id': self.import_attachment3_xlsx._id },
        ]
        self.rep_link = r'(?<!\\|\!)\[(?P<title>.+?(?<!\\)(?:\\\\)*)\]\((?P<path>.+?)(?<!\\)\)'
        self.rep_image = r'(?<!\\)!\[(?P<title>.*?(?<!\\)(?:\\\\)*)\]\((?P<path>.+?)(?<!\\)\)'
        self.guid = self.project.guids.first()._id
        self.wiki_page1 = WikiPage.objects.create_for_node(self.project, 'wiki page1', 'wiki page1 content', self.consolidate_auth)
        self.wiki_page2 = WikiPage.objects.create_for_node(self.project, 'wiki page2', 'wiki page2 content', self.consolidate_auth, self.wiki_page1)


    def test_replace_wiki_image_no_image_matches(self):
        wiki_content_none_image = 'Wiki content'
        no_image_matches = []
        wiki_content = views._replace_wiki_image(self.project, no_image_matches, wiki_content_none_image, self.wiki_info, self.root_import_folder1._id, self.node_file_mapping)
        self.assertEqual(wiki_content, wiki_content_none_image)

    def test_replace_wiki_image_one_image_match(self):
        wiki_content_one_image = 'Wiki content with ![](image1.png)'
        self.one_image_matches = list(re.finditer(self.rep_image, wiki_content_one_image))
        expected_content = f'Wiki content with ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render)'
        wiki_content = views._replace_wiki_image(self.project, self.one_image_matches, wiki_content_one_image, self.wiki_info, self.root_import_folder1._id, self.node_file_mapping)
        self.assertEqual(wiki_content, expected_content)

    def test_replace_wiki_image_two_image_matches(self):
        wiki_content_two_image = 'Wiki content with ![](image1.png) and ![](image2.png)'
        self.two_image_matches = list(re.finditer(self.rep_image, wiki_content_two_image))
        expected_content = f'Wiki content with ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render) and ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image2._id}?mode=render)'
        wiki_content = views._replace_wiki_image(self.project, self.two_image_matches, wiki_content_two_image, self.wiki_info, self.root_import_folder1._id, self.node_file_mapping)
        self.assertEqual(wiki_content, expected_content)

    def test_replace_wiki_image_match_with_slash(self):
        wiki_content_image_with_slash = 'Wiki content with ![](ima/ge3.png)'
        self.slash_image_matches = list(re.finditer(self.rep_image, wiki_content_image_with_slash))
        expected_content = wiki_content_image_with_slash = 'Wiki content with ![](ima/ge3.png)'
        wiki_content = views._replace_wiki_image(self.project, self.slash_image_matches, wiki_content_image_with_slash, self.wiki_info, self.root_import_folder1._id, self.node_file_mapping)
        self.assertEqual(wiki_content, expected_content)

    def test_replace_file_name_image_with_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png "tooltip1")'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render "tooltip1")'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_file_name_image_without_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render)'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_file_name_link_with_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_link_tooltip = 'Wiki content with [attachment1.doc](attachment1.doc "tooltip1")'
        match = list(re.finditer(self.rep_link, wiki_content_link_tooltip))[0]
        notation = 'link'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with [attachment1.doc]({website_settings.DOMAIN}{self.guid}/files/osfstorage/{self.import_attachment1_doc._id} "tooltip1")'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_link_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_file_name_link_without_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_link_tooltip = 'Wiki content with [attachment1.doc](attachment1.doc)'
        match = list(re.finditer(self.rep_link, wiki_content_link_tooltip))[0]
        notation = 'link'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with [attachment1.doc]({website_settings.DOMAIN}{self.guid}/files/osfstorage/{self.import_attachment1_doc._id})'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_link_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_with_not_existing_file_id(self):
        wiki_name = 'not_exisiting.txt'
        wiki_content_link_tooltip = 'Wiki content with [not_exisiting.txt](not_exisiting.txt)'
        match = list(re.finditer(self.rep_link, wiki_content_link_tooltip))[0]
        notation = 'link'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = wiki_content_link_tooltip
        result = views._replace_file_name(self.project, wiki_name, wiki_content_link_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_wiki_link_notation_wiki_page_with_tooptip(self):
        wiki_content_link = 'Wiki content with [wiki page1](wiki%20page1 "tooltip1")'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = f'Wiki content with [wiki page1](../wiki%20page1/ "tooltip1")'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_wiki_page_without_tooptip(self):
        wiki_content_link = 'Wiki content with [wiki page1](wiki%20page1)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = f'Wiki content with [wiki page1](../wiki%20page1/)'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_attachment_file(self):
        wiki_content_link_attachment = 'Wiki content with [attachment1.doc](attachment1.doc)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_attachment))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = f'Wiki content with [attachment1.doc]({website_settings.DOMAIN}{self.guid}/files/osfstorage/{self.import_attachment1_doc._id})'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_attachment, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_has_slash(self):
        wiki_content_link_has_slash = 'Wiki content with [wiki/page](wiki/page)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_has_slash))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = wiki_content_link_has_slash
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_has_slash, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_has_sharp(self):
        wiki_content_link_has_sharp = 'Wiki content with [wiki#page](#wikipage)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_has_sharp))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = wiki_content_link_has_sharp
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_has_sharp, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_is_url(self):
        wiki_content_link_is_url = 'Wiki content with [example](https://example.com)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_is_url))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = wiki_content_link_is_url
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_is_url, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_has_sharp_dot(self):
        wiki_content_link_has_sharp_dot = 'Wiki content with [wiki#page.txt](wiki#page.txt)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_has_sharp_dot))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = f'Wiki content with [wiki#page.txt]({website_settings.DOMAIN}{self.guid}/files/osfstorage/{self.import_attachment2_txt._id})'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_has_sharp_dot, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_no_link(self):
        wiki_content = 'Wiki content'
        link_matches = list(re.finditer(self.rep_link, wiki_content))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = wiki_content
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_check_wiki_name_exist_existing_wiki(self):
        wiki_name = 'wiki%20page1'
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_content = views._check_wiki_name_exist(self.project, wiki_name, self.node_file_mapping, import_wiki_name_list)
        self.assertTrue(result_content)

    def test_check_wiki_name_exist_import_directory(self):
        wiki_name = 'importpage1'
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_content = views._check_wiki_name_exist(self.project, wiki_name, self.node_file_mapping, import_wiki_name_list)
        self.assertTrue(result_content)

    def test_check_wiki_name_exist_not_existing(self):
        wiki_name = 'not%20existing%20wiki'
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_content = views._check_wiki_name_exist(self.project, wiki_name, self.node_file_mapping, import_wiki_name_list)
        self.assertFalse(result_content)

    def test_check_wiki_name_exist_existing_wiki_nfd(self):
        wiki_name = 'wiki%20page1'
        wiki_name_nfd = unicodedata.normalize('NFD', wiki_name)
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_content = views._check_wiki_name_exist(self.project, wiki_name_nfd, self.node_file_mapping, import_wiki_name_list)
        self.assertTrue(result_content)

    def test_check_attachment_file_name_exist_has_hat(self):
        wiki_name = 'importpage1'
        file_name = 'importpage2^attachment3.xlsx'
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_id = views._check_attachment_file_name_exist(wiki_name, file_name, self.root_import_folder1._id, self.node_file_mapping)
        self.assertEqual(result_id, self.import_attachment3_xlsx._id)

    def test_check_attachment_file_name_exist_has_not_hat(self):
        wiki_name = 'importpage1'
        file_name = 'attachment1.doc'
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_id = views._check_attachment_file_name_exist(wiki_name, file_name, self.root_import_folder1._id, self.node_file_mapping)
        self.assertEqual(result_id, self.import_attachment1_doc._id)

    def test_process_attachment_file_name_exist(self):
        wiki_name = 'importpage1'
        file_name = 'attachment1.doc'
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_id = views._process_attachment_file_name_exist(wiki_name, file_name, self.root_import_folder1._id, self.node_file_mapping)
        self.assertEqual(result_id, self.import_attachment1_doc._id)

    def test_process_attachment_file_name_exist_nfd(self):
        wiki_name = 'importpage1'
        file_name = 'attachment1.doc'
        wiki_name_nfd = unicodedata.normalize('NFD', wiki_name)
        file_name_nfd = unicodedata.normalize('NFD', file_name)
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_id = views._process_attachment_file_name_exist(wiki_name_nfd, file_name_nfd, self.root_import_folder1._id, self.node_file_mapping)
        self.assertEqual(result_id, self.import_attachment1_doc._id)

    def test_process_attachment_file_name_exist_not_exist(self):
        wiki_name = 'importpage1'
        file_name = 'not_existing_file.doc'
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_content = views._process_attachment_file_name_exist(wiki_name, file_name, self.root_import_folder1._id, self.node_file_mapping)
        self.assertIsNone(result_content)

class TestGetMdContentFromWb(OsfTestCase):
    def setUp(self):
        super(TestGetMdContentFromWb, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)

    @mock.patch('requests.get')
    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_get_md_content_from_wb_success(self, mock_task, mock_get):
        mock_response = b'test content'
        mock_get.return_value = MockWbResponse(mock_response, 200)
        mock_task.is_aborted.return_value = False
        data = [{'wiki_name': 'wikipage1', '_id': 'qwe'}]
        creator, creator_auth = get_creator_auth_header(self.user)
        result = views._get_md_content_from_wb(data, self.project, creator_auth, mock_task)
        self.assertEqual(result[0]['wiki_content'], 'test content')

    @mock.patch('requests.get')
    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_get_md_content_from_wb_fail(self, mock_task, mock_get):
        mock_response = {}
        mock_get.return_value = MockWbResponse(mock_response, 400)
        mock_task.is_aborted.return_value = False
        data = [{'wiki_name': 'wikipage2', '_id': 'rty'}]
        creator, creator_auth = get_creator_auth_header(self.user)
        result = views._get_md_content_from_wb(data, self.project, creator_auth, mock_task)
        self.assertEqual(result, [{'wiki_name': 'wikipage2', '_id': 'rty'}])

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult')
    def test_get_md_content_from_wb_aborted(self, mock_task):
        mock_task.is_aborted.return_value = True
        data = [{'wiki_name': 'wikipage1', '_id': 'qwe'}]
        creator, creator_auth = get_creator_auth_header(self.user)
        result = views._get_md_content_from_wb(data, self.project, creator_auth, mock_task)
        self.assertIsNone(result)

class TestExcludeSymbols(OsfTestCase):
    def test_has_slash(self):
        path = 'meeting 4/24'
        result = views._exclude_symbols(path)
        self.assertTrue(result[0])
        self.assertFalse(result[1])
        self.assertFalse(result[2])
        self.assertFalse(result[3])

    def test_has_sharp(self):
        path = '#contents'
        result = views._exclude_symbols(path)
        self.assertFalse(result[0])
        self.assertTrue(result[1])
        self.assertFalse(result[2])
        self.assertFalse(result[3])

    def test_is_url(self):
        path = 'https://example.com'
        result = views._exclude_symbols(path)
        self.assertTrue(result[0])
        self.assertFalse(result[1])
        self.assertTrue(result[2])
        self.assertTrue(result[3])

    def test_has_dot(self):
        path = 'file.txt'
        result = views._exclude_symbols(path)
        self.assertFalse(result[0])
        self.assertFalse(result[1])
        self.assertTrue(result[2])
        self.assertFalse(result[3])

    def test_has_sharp_and_dot(self):
        path = 'file#0424.txt'
        result = views._exclude_symbols(path)
        self.assertFalse(result[0])
        self.assertTrue(result[1])
        self.assertTrue(result[2])
        self.assertFalse(result[3])

class TestReplaceCommonRule(OsfTestCase):
    def test_plus_sign_replacement(self):
        input_name = 'my+example+file.txt'
        expected_output = 'my example file.txt'
        actual_output = views._replace_common_rule(input_name)
        self.assertEqual(actual_output, expected_output)

    def test_url_decoding(self):
        input_name = 'my%20example%20file.txt'
        expected_output = 'my example file.txt'
        actual_output = views._replace_common_rule(input_name)
        self.assertEqual(actual_output, expected_output)

    def test_mixed_url_decoding(self):
        input_name = 'another%2Bexample%2Bfile.txt'
        expected_output = 'another+example+file.txt'
        actual_output = views._replace_common_rule(input_name)
        self.assertEqual(actual_output, expected_output)

    def test_no_special_characters(self):
        input_name = 'no_special_characters.txt'
        expected_output = 'no_special_characters.txt'
        actual_output = views._replace_common_rule(input_name)
        self.assertEqual(actual_output, expected_output)

    def test_special_characters_with_spaces(self):
        input_name = 'special%20%2B%20characters.txt'
        expected_output = 'special + characters.txt'
        actual_output = views._replace_common_rule(input_name)
        self.assertEqual(actual_output, expected_output)

class TestExcludeTooltip(OsfTestCase):
    def test_no_tooltip(self):
        match_path = 'test.txt'
        expected_path = 'test.txt'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        self.assertEqual(result_path, expected_path)
        self.assertIsNone(result_tooptip)

    def test_single_quote_tooltip(self):
        match_path = "test.txt 'tooltip'"
        expected_path = 'test.txt'
        expected_tooltip = 'tooltip'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        self.assertEqual(result_path, expected_path)
        self.assertEqual(result_tooptip['tooltip'], expected_tooltip)

    def test_double_quote_tooltip(self):
        match_path = 'test.txt "tooltip"'
        expected_path = 'test.txt'
        expected_tooltip = 'tooltip'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        self.assertEqual(result_path, expected_path)
        self.assertEqual(result_tooptip['tooltip'], expected_tooltip)

    def test_backslash_in_tooltip(self):
        match_path = r'test.txt "to\\\\ol\"\\tip"'
        expected_path = 'test.txt'
        expected_tooltip = 'to\\\\\\\\ol\\"\\\\tip'
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        self.assertEqual(result_path, expected_path)
        self.assertEqual(result_tooptip['tooltip'], expected_tooltip)

    def test_empty_tooltip(self):
        match_path = 'test.txt ""'
        expected_path = 'test.txt'
        expected_tooltip = ''
        result_path, result_tooptip = views._exclude_tooltip(match_path)
        self.assertEqual(result_path, expected_path)
        self.assertEqual(result_tooptip['tooltip'], expected_tooltip)

class TestExtractErrMsg(OsfTestCase):
    def test_err_with_tab(self):
        err_obj_con = "code=400, data={'message_short': 'Error Message with Tab', 'message_long': '\\tAn error occures with tab\\t', 'code': 400, 'referrer': None}"
        err = CeleryError(err_obj_con)
        expected_msg = 'An error occures with tab'
        result_msg = views._extract_err_msg(err)
        self.assertEqual(result_msg, expected_msg)

    def test_err_without_tab(self):
        err_obj_con = 'An error occurred'
        err = CeleryError(err_obj_con)
        result_msg = views._extract_err_msg(err)
        self.assertIsNone(result_msg)

class TestGetMaxDepth(OsfTestCase):
    def test_same_depth(self):
        wiki_infos = [
            {'path': '/page1/page2/page3'},
            {'path': '/page4/page5/page6'},
            {'path': '/page7/page8/page9'}
        ]
        max_depth = views._get_max_depth(wiki_infos)
        self.assertEqual(max_depth, 2)

    def test_different_depth(self):
        wiki_infos = [
            {'path': '/page1/page2/page3'},
            {'path': '/page4/page5'},
            {'path': '/page6'}
        ]
        max_depth = views._get_max_depth(wiki_infos)
        self.assertEqual(max_depth, 2)

    def test_single_element(self):
        wiki_infos = [
            {'path': '/page1'}
        ]
        max_depth = views._get_max_depth(wiki_infos)
        self.assertEqual(max_depth, 0)

class TestCreateImportErrorList(OsfTestCase):

    def test_empty_return(self):
        wiki_infos = [{'path': '/page1'},{'path': '/page2'}]
        imported_list = [{'path': '/page1'},{'path': '/page2'}]
        import_errors = views._create_import_error_list(wiki_infos, imported_list)
        self.assertEqual(import_errors, [])

    def test_non_empty_return(self):
        wiki_infos = [{'path': '/path1'}, {'path': '/path2'}, {'path': '/path3'}]
        imported_list = [{'path': '/path1'}]
        import_errors = views._create_import_error_list(wiki_infos, imported_list)
        self.assertIn('/path2', import_errors)
        self.assertIn('/path3', import_errors)

class TestTaskStatus(OsfTestCase):
    def setUp(self):
        super(TestTaskStatus, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.consolidate_auth = Auth(user=self.project.creator)
        WikiImportTask.objects.create(node=self.project, task_id='task-id-1111', status=WikiImportTask.STATUS_COMPLETED, creator=self.user)

    def test_project_clean_celery_task_none_running_task(self):
        url = self.project.api_url_for('project_clean_celery_tasks')
        res = self.app.post(url, auth=self.user.auth)
        task_completed = WikiImportTask.objects.get(task_id='task-id-1111')
        self.assertEqual(task_completed.status, 'Completed')

    def test_project_clean_celery_task_one_running_task(self):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-2222', status=WikiImportTask.STATUS_RUNNING, creator=self.user)
        url = self.project.api_url_for('project_clean_celery_tasks')
        res = self.app.post(url, auth=self.user.auth)
        task_completed = WikiImportTask.objects.get(task_id='task-id-1111')
        task_running = WikiImportTask.objects.get(task_id='task-id-2222')
        self.assertEqual(task_completed.status, 'Completed')
        self.assertEqual(task_running.status, 'Stopped')

    def test_project_clean_celery_task_two_running_task(self):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-3333', status=WikiImportTask.STATUS_RUNNING, creator=self.user)
        WikiImportTask.objects.create(node=self.project, task_id='task-id-4444', status=WikiImportTask.STATUS_RUNNING, creator=self.user)
        url = self.project.api_url_for('project_clean_celery_tasks')
        res = self.app.post(url, auth=self.user.auth)
        task_completed = WikiImportTask.objects.get(task_id='task-id-1111')
        task_running1 = WikiImportTask.objects.get(task_id='task-id-3333')
        task_running2 = WikiImportTask.objects.get(task_id='task-id-4444')
        self.assertEqual(task_completed.status, 'Completed')
        self.assertEqual(task_running1.status, 'Stopped')
        self.assertEqual(task_running2.status, 'Stopped')

    def test_project_clean_celery_with_no_admin_permission(self):
        url = self.project.api_url_for('project_clean_celery_tasks')
        res = self.app.post(url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_get_abort_wiki_import_result_already_aborted(self):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-5555', status=WikiImportTask.STATUS_STOPPED, process_end=datetime.datetime(2024, 5, 1, 11, 00, tzinfo=pytz.utc), creator=self.user)
        WikiImportTask.objects.create(node=self.project, task_id='task-id-6666', status=WikiImportTask.STATUS_STOPPED, process_end=datetime.datetime(2024, 5, 1, 9, 00, tzinfo=pytz.utc), creator=self.user)
        url = self.project.api_url_for('project_get_abort_wiki_import_result')
        res = self.app.get(url, auth=self.user.auth)
        json_string = res._app_iter[0].decode('utf-8')
        result = json.loads(json_string)
        self.assertEqual(result, {'aborted': True})

    def test_get_abort_wiki_import_result_not_yet_aborted(self):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-7777', status=WikiImportTask.STATUS_STOPPED, process_end=datetime.datetime(2024, 5, 1, 8, 00, tzinfo=pytz.utc), creator=self.user)
        WikiImportTask.objects.create(node=self.project, task_id='task-id-8888', status=WikiImportTask.STATUS_STOPPED, creator=self.user)
        url = self.project.api_url_for('project_get_abort_wiki_import_result')
        res = self.app.get(url, auth=self.user.auth)
        json_string = res._app_iter[0].decode('utf-8')
        result = json.loads(json_string)
        self.assertIsNone(result)

    def test_get_abort_wiki_import_result_with_no_admin_permission(self):
        url = self.project.api_url_for('project_get_abort_wiki_import_result')
        res = self.app.post(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_check_running_task_one(self):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-9999', status=WikiImportTask.STATUS_RUNNING, creator=self.user)
        views.check_running_task('task-id-9999', self.project)
        task_running = WikiImportTask.objects.get(task_id='task-id-9999')
        self.assertEqual(task_running.status, 'Running')

    def test_check_running_task_two(self):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-aaaa', status=WikiImportTask.STATUS_RUNNING, creator=self.user)
        WikiImportTask.objects.create(node=self.project, task_id='task-id-bbbb', status=WikiImportTask.STATUS_RUNNING, creator=self.user)
        with self.assertRaises(HTTPError) as cm:
            views.check_running_task('task-id-aaaa', self.project)
        # HTTPErrorの中身がWIKI_IMPORT_TASK_ALREADY_EXISTSのメッセージを持つか確認
        self.assertEqual(cm.exception.data['message_short'], 'Running Task exists')
        self.assertEqual(cm.exception.data['message_long'], '\tOnly 1 wiki import task can be executed on 1 node\t')
        task_running = WikiImportTask.objects.get(task_id='task-id-aaaa')
        self.assertEqual(task_running.status, 'Error')

    @freeze_time('2024-05-01 12:00:00')
    def test_change_task_status(self):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-cccc', status=WikiImportTask.STATUS_COMPLETED, creator=self.user)
        views.change_task_status('task-id-cccc', WikiImportTask.STATUS_COMPLETED, True)
        task_running = WikiImportTask.objects.get(task_id='task-id-cccc')
        self.assertEqual(task_running.status, 'Completed')
        self.assertEqual(task_running.process_end, timezone.make_aware(datetime.datetime(2024, 5, 1, 12, 0, 0)))

    def test_set_wiki_import_task_proces_end_no_tasks_to_update(self):
        views.set_wiki_import_task_proces_end(self.project)
        self.assertEqual(WikiImportTask.objects.count(), 1)

    @freeze_time('2024-05-01 12:00:00')
    def test_one_task_to_update(self):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-dddd', status=WikiImportTask.STATUS_STOPPED, creator=self.user)
        views.set_wiki_import_task_proces_end(self.project)
        task_stopped = WikiImportTask.objects.get(task_id='task-id-dddd')
        self.assertAlmostEqual(task_stopped.process_end, timezone.make_aware(datetime.datetime(2024, 5, 1, 12, 0, 0)))

    @freeze_time('2024-05-01 12:00:00')
    def test_one_task_to_update(self):
        WikiImportTask.objects.create(node=self.project, task_id='task-id-eeee', status=WikiImportTask.STATUS_STOPPED, creator=self.user)
        WikiImportTask.objects.create(node=self.project, task_id='task-id-ffff', status=WikiImportTask.STATUS_STOPPED, creator=self.user)
        views.set_wiki_import_task_proces_end(self.project)
        task_stopped1 = WikiImportTask.objects.get(task_id='task-id-eeee')
        task_stopped2 = WikiImportTask.objects.get(task_id='task-id-ffff')
        self.assertAlmostEqual(task_stopped1.process_end, timezone.make_aware(datetime.datetime(2024, 5, 1, 12, 0, 0)))
        self.assertAlmostEqual(task_stopped2.process_end, timezone.make_aware(datetime.datetime(2024, 5, 1, 12, 0, 0)))

class TestWikiPageSort(OsfTestCase):

    def setUp(self):
        super(TestWikiPageSort, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.wiki_page1 = WikiPage.objects.create_for_node(self.project, 'wiki page1', 'wiki page1 content', self.consolidate_auth)
        self.wiki_page2 = WikiPage.objects.create_for_node(self.project, 'wiki page2', 'wiki page2 content', self.consolidate_auth)
        self.wiki_child_page1 = WikiPage.objects.create_for_node(self.project, 'wiki child page1', 'wiki child page1 content', self.consolidate_auth, self.wiki_page2)
        self.wiki_child_page2 = WikiPage.objects.create_for_node(self.project, 'wiki child page2', 'wiki child page2 content', self.consolidate_auth, self.wiki_page2)
        self.wiki_child_page3 = WikiPage.objects.create_for_node(self.project, 'wiki child page3', 'wiki child page3 content', self.consolidate_auth, self.wiki_page2)
        self.guid1 = self.wiki_page1.guids.first()._id
        self.guid2 = self.wiki_page2.guids.first()._id
        self.child_guid1 = self.wiki_child_page1.guids.first()._id
        self.child_guid2 = self.wiki_child_page2.guids.first()._id
        self.child_guid3 = self.wiki_child_page3.guids.first()._id

    def test_sorted_data_single(self):
        sorted_data = [{'name': 'testd', 'id': 'hbrw7', 'sortOrder': 1, 'children': [], 'fold': False}, {'name': 'testc', 'id': 'rphfv', 'sortOrder': 2, 'children': [], 'fold': False}]
        id_list, sort_list, parent_wiki_id_list = views._get_sorted_list(sorted_data, None)
        self.assertEqual(id_list, ['hbrw7', 'rphfv'])
        self.assertEqual(sort_list, [1,2])
        self.assertEqual(parent_wiki_id_list, [None, None])

    def test_sorted_data_nest(self):
        sorted_data = [{'name': 'tsta', 'id': '97xuz', 'sortOrder': 1, 'children': [], 'fold': False}, {'name': 'tstb', 'id': 'gwd9u', 'sortOrder': 2, 'children': [{'name': 'child1', 'id': '5fhdq', 'sortOrder': 1, 'children': [], 'fold': False}, {'name': 'child2', 'id': 'x38vh', 'sortOrder': 2, 'children': [{'name': 'grandchilda', 'id': '64au2', 'sortOrder': 1, 'children': [], 'fold': False}], 'fold': False}], 'fold': False}]
        id_list, sort_list, parent_wiki_id_list = views._get_sorted_list(sorted_data, None)
        self.assertEqual(id_list, ['97xuz', 'gwd9u', '5fhdq', 'x38vh', '64au2'])
        self.assertEqual(sort_list, [1, 2, 1, 2, 1])
        self.assertEqual(parent_wiki_id_list, [None, None, 'gwd9u', 'gwd9u', 'x38vh'])

    def test_bulk_update_wiki_sort(self):
        sort_id_list = [self.guid1, self.guid2, self.child_guid2, self.child_guid3, self.child_guid1]
        sort_num_list = [1, 2, 1, 1, 3]
        parent_wiki_id_list = [None, None, self.guid2, self.child_guid2, None]
        views._bulk_update_wiki_sort(self.project, sort_id_list, sort_num_list, parent_wiki_id_list)
        result_wiki_page1 = WikiPage.objects.filter(page_name='wiki page1').values('parent_id', 'sort_order').first()
        result_wiki_page2 = WikiPage.objects.filter(page_name='wiki page2').values('parent_id', 'sort_order').first()
        result_wiki_child_page1 = WikiPage.objects.filter(page_name='wiki child page1').values('parent_id', 'sort_order').first()
        result_wiki_child_page2 = WikiPage.objects.filter(page_name='wiki child page2').values('parent_id', 'sort_order').first()
        result_wiki_child_page3 = WikiPage.objects.filter(page_name='wiki child page3').values('parent_id', 'sort_order').first()
        wiki_page2_id = self.wiki_page2.id
        wiki_child_page2_id = self.wiki_child_page2.id
        self.assertEqual(result_wiki_page1, {'parent_id': None, 'sort_order': 1})
        self.assertEqual(result_wiki_page2, {'parent_id': None, 'sort_order': 2})
        self.assertEqual(result_wiki_child_page1, {'parent_id': None, 'sort_order': 3})
        self.assertEqual(result_wiki_child_page2, {'parent_id': wiki_page2_id, 'sort_order': 1})
        self.assertEqual(result_wiki_child_page3, {'parent_id': wiki_child_page2_id, 'sort_order': 1})

    def test_project_update_wiki_page_sort(self):
        url = self.project.api_url_for('project_update_wiki_page_sort')
        res = self.app.post_json(url, { 'sortedData': [{'name': 'wiki page1', 'id': self.guid1, 'sortOrder': 1, 'children': [], 'fold': False}, {'name': 'wiki page2', 'id': self.guid2, 'sortOrder': 2, 'children': [{'name': 'wiki child page1', 'id': self.child_guid1, 'sortOrder': 1, 'children': [], 'fold': False}, {'name': 'wiki child page2', 'id': self.child_guid2, 'sortOrder': 2, 'children': [{'name': 'wiki child page3', 'id': self.child_guid3, 'sortOrder': 1, 'children': [], 'fold': False}], 'fold': False}], 'fold': False}]}, auth=self.user.auth)
        result_wiki_page1 = WikiPage.objects.filter(page_name='wiki page1').values('parent_id', 'sort_order').first()
        result_wiki_page2 = WikiPage.objects.filter(page_name='wiki page2').values('parent_id', 'sort_order').first()
        result_wiki_child_page1 = WikiPage.objects.filter(page_name='wiki child page1').values('parent_id', 'sort_order').first()
        result_wiki_child_page2 = WikiPage.objects.filter(page_name='wiki child page2').values('parent_id', 'sort_order').first()
        result_wiki_child_page3 = WikiPage.objects.filter(page_name='wiki child page3').values('parent_id', 'sort_order').first()
        wiki_page2_id = self.wiki_page2.id
        wiki_child_page2_id = self.wiki_child_page2.id
        self.assertEqual(result_wiki_page1, {'parent_id': None, 'sort_order': 1})
        self.assertEqual(result_wiki_page2, {'parent_id': None, 'sort_order': 2})
        self.assertEqual(result_wiki_child_page1, {'parent_id': wiki_page2_id, 'sort_order': 1})
        self.assertEqual(result_wiki_child_page2, {'parent_id': wiki_page2_id, 'sort_order': 2})
        self.assertEqual(result_wiki_child_page3, {'parent_id': wiki_child_page2_id, 'sort_order': 1})
