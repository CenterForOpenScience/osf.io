# -*- coding: utf-8 -*-
# TODO: Port to pytest

# PEP8 asserts
from copy import deepcopy
import httplib as http
import time
import mock
import pytest
import pytz
import datetime

from nose.tools import *  # noqa

from tests.base import OsfTestCase, fake
from osf_tests.factories import (
    UserFactory, NodeFactory, ProjectFactory,
    AuthUserFactory, RegistrationFactory
)
from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory

from osf.exceptions import NodeStateError
from osf.utils.permissions import ADMIN, WRITE, READ
from addons.wiki import settings
from addons.wiki import views
from addons.wiki.exceptions import InvalidVersionError
from addons.wiki.models import WikiPage, WikiVersion, render_content
from addons.wiki.utils import (
    get_sharejs_uuid, generate_private_uuid, share_db, delete_share_doc,
    migrate_uuid, format_wiki_version, serialize_wiki_settings, serialize_wiki_widget
)
from framework.auth import Auth
from django.utils import timezone
from addons.wiki.utils import to_mongo_key

from .config import EXAMPLE_DOCS, EXAMPLE_OPS

pytestmark = pytest.mark.django_db

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
        res = self.app.post(url, {'content': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        # page was updated with new content
        new_wiki = WikiVersion.objects.get_for_node(self.project, 'home')
        assert_equal(new_wiki.content, 'new content')

    def test_project_wiki_edit_post_with_new_wname_and_no_content(self):
        # note: forward slashes not allowed in page_name
        page_name = fake.catch_phrase().replace('/', ' ')
        old_wiki_page_count = WikiVersion.objects.all().count()
        url = self.project.web_url_for('project_wiki_edit_post', wname=page_name)
        # User submits to edit form with no content
        res = self.app.post(url, {'content': ''}, auth=self.user.auth).follow()
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
        res = self.app.post(url, {'content': page_content}, auth=self.user.auth).follow()
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
        res = self.app.post(url, {'content': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        wiki = WikiPage.objects.get_for_node(self.project, new_wname)
        assert_equal(wiki.page_name, new_wname)

        # updating content should return correct url as well.
        res = self.app.post(url, {'content': 'updated content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

    def test_project_wiki_edit_post_with_special_characters(self):
        new_wname = 'title: ' + SPECIAL_CHARACTERS_ALLOWED
        new_wiki_content = 'content: ' + SPECIAL_CHARACTERS_ALL
        url = self.project.web_url_for('project_wiki_edit_post', wname=new_wname)
        res = self.app.post(url, {'content': new_wiki_content}, auth=self.user.auth).follow()
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
        res = self.app.post(url, {'content': 'blah'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        self.project.reload()
        wiki =  WikiVersion.objects.get_for_node(self.project, 'cupcake')
        assert_is_not_none(wiki)

    def test_wiki_validate_name(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='Capslock')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

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
        assert_in('...', res['wiki_content'])
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
        assert_not_in('data-osf-panel="Edit"', res.text)
        # Write permissions
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_in('data-osf-panel="Edit"', res.text)
        # Publicly editable
        wiki = self.project.get_addon('wiki')
        wiki.set_editing(permissions=True, auth=self.consolidate_auth, log=True)
        res = self.app.get(url, auth=AuthUserFactory().auth)
        assert_equal(res.status_code, 200)
        assert_in('data-osf-panel="Edit"', res.text)
        # Publicly editable but not logged in
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_not_in('data-osf-panel="Edit"', res.text)

    def test_wiki_widget_not_show_in_registration_for_contributor(self):
        registration = RegistrationFactory(project=self.project)
        res = self.app.get(
            registration.web_url_for('view_project'),
            auth=self.user.auth
        )
        assert_equal(res.status_code, 200)
        assert_not_in('Add important information, links, or images here to describe your project.', res.text)


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
        assert_equal(http.BAD_REQUEST, res.status_code)
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
        assert_not_in(private_uuid, res.body)
        assert_in(get_sharejs_uuid(self.project, self.wname), res.body)

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
        assert_not_in(private_uuid, res.body)
        assert_in(get_sharejs_uuid(self.project, self.wname), res.body)

        # Users without write permission should not be able to access
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_not_in(get_sharejs_uuid(self.project, self.wname), res.body)

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
        assert_in(original_sharejs_uuid, res.body)

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
        assert_not_in(original_sharejs_uuid, res.body)


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
                    'id': zoo_page._primary_key,
                }
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
                        }
                    },
                    {
                        'page': {
                            'url': self.component.web_url_for('project_wiki_view', wname='zoo', _guid=True),
                            'name': 'zoo',
                            'id': zoo_page._primary_key,
                        },
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
