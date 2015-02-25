# -*- coding: utf-8 -*-

# PEP8 asserts
from copy import deepcopy
import httplib as http

import mock
import time

from nose.tools import *  # noqa
from modularodm.exceptions import ValidationValueError

from tests.base import OsfTestCase, fake
from tests.factories import (
    UserFactory, NodeFactory, ProjectFactory, ApiKeyFactory,
    AuthUserFactory, NodeWikiFactory,
)

from website.addons.wiki import settings
from website.addons.wiki.exceptions import InvalidVersionError
from website.addons.wiki.views import _serialize_wiki_toc, _get_wiki_web_urls, _get_wiki_api_urls
from website.addons.wiki.model import NodeWikiPage, render_content
from website.addons.wiki.utils import (
    get_sharejs_uuid, generate_private_uuid, share_db, delete_share_doc,
    migrate_uuid, format_wiki_version,
)
from website.addons.wiki.tests.config import EXAMPLE_DOCS, EXAMPLE_OPS
from framework.auth import Auth
from framework.mongo.utils import to_mongo_key

# forward slashes are not allowed, typically they would be replaced with spaces
SPECIAL_CHARACTERS_ALL = u'`~!@#$%^*()-=_+ []{}\|/?.df,;:''"'
SPECIAL_CHARACTERS_ALLOWED = u'`~!@#$%^*()-=_+ []{}\|?.df,;:''"'


class TestNodeWikiPageModel(OsfTestCase):

    def test_page_name_cannot_be_greater_than_100_characters(self):
        bad_name = 'a' * 101
        page = NodeWikiPage(page_name=bad_name)
        with assert_raises(ValidationValueError):
            page.save()


class TestWikiViews(OsfTestCase):

    def setUp(self):
        super(TestWikiViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.consolidate_auth = Auth(user=self.project.creator)

    def test_wiki_url_get_returns_200(self):
        url = self.project.web_url_for('project_wiki_view', wname='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_url_404_with_no_write_permission(self):
        url = self.project.web_url_for('project_wiki_view', wname='somerandomid')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_wiki_deleted_404_with_no_write_permission(self, mock_sharejs):
        self.project.update_node_wiki('funpage', 'Version 1', Auth(self.user))
        self.project.save()
        url = self.project.web_url_for('project_wiki_view', wname='funpage')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        delete_url = self.project.api_url_for('project_wiki_delete', wname='funpage')
        self.app.delete(delete_url, auth=self.user.auth)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_wiki_url_with_path_get_returns_200(self):
        self.project.update_node_wiki('funpage', 'Version 1', Auth(self.user))
        self.project.update_node_wiki('funpage', 'Version 2', Auth(self.user))
        self.project.save()

        url = self.project.web_url_for(
            'project_wiki_view',
            wname='funpage',
        ) + '?view&compare=1&edit'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_wiki_url_with_edit_get_returns_404_with_no_write_permission(self):
        self.project.update_node_wiki('funpage', 'Version 1', Auth(self.user))
        self.project.update_node_wiki('funpage', 'Version 2', Auth(self.user))
        self.project.save()

        url = self.project.web_url_for(
            'project_wiki_view',
            wname='funpage',
            compare=1,
        )
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

        url = self.project.web_url_for(
            'project_wiki_view',
            wname='funpage',
        ) + '?edit'
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_wiki_url_for_pointer_returns_200(self):
        # TODO: explain how this tests a pointer
        project = ProjectFactory(is_public=True)
        self.project.add_pointer(project, Auth(self.project.creator), save=True)
        url = self.project.web_url_for('project_wiki_view', wname='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_draft_returns_200(self):
        url = self.project.api_url_for('wiki_page_draft', wname='somerandomid')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_wiki_content_returns_200(self):
        url = self.project.api_url_for('wiki_page_content', wname='somerandomid')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    @mock.patch('website.addons.wiki.model.NodeWikiPage.rendered_before_update', new_callable=mock.PropertyMock)
    def test_wiki_content_use_python_render(self, mock_rendered_before_update):
        content = 'Some content'
        self.project.update_node_wiki('somerandomid', content, Auth(self.user))
        self.project.save()

        mock_rendered_before_update.return_value = True
        url = self.project.api_url_for('wiki_page_content', wname='somerandomid')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(content, res.json['wiki_content'])
        assert_in(content, res.json['wiki_rendered'])

        mock_rendered_before_update.return_value = False
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(content, res.json['wiki_content'])
        assert_equal('', res.json['wiki_rendered'])


    def test_wiki_url_for_component_returns_200(self):
        component = NodeFactory(project=self.project, is_public=True)
        url = component.web_url_for('project_wiki_view', wname='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_serialize_wiki_toc(self):
        project = ProjectFactory()
        auth = Auth(project.creator)
        NodeFactory(project=project, creator=project.creator)
        no_wiki = NodeFactory(project=project, creator=project.creator)
        project.save()

        serialized = _serialize_wiki_toc(project, auth=auth)
        assert_equal(len(serialized), 2)
        no_wiki.delete_addon('wiki', auth=auth)
        serialized = _serialize_wiki_toc(project, auth=auth)
        assert_equal(len(serialized), 1)

    def test_get_wiki_url_pointer_component(self):
        """Regression test for issues
        https://github.com/CenterForOpenScience/osf/issues/363 and
        https://github.com/CenterForOpenScience/openscienceframework.org/issues/574

        """
        user = UserFactory()
        pointed_node = NodeFactory(creator=user)
        project = ProjectFactory(creator=user)
        auth = Auth(user=user)
        project.add_pointer(pointed_node, auth=auth, save=True)

        serialized = _serialize_wiki_toc(project, auth)
        assert_equal(
            serialized[0]['url'],
            pointed_node.web_url_for('project_wiki_view', wname='home', _guid=True)
        )

    def test_project_wiki_edit_post(self):
        self.project.update_node_wiki(
            'home',
            content='old content',
            auth=Auth(self.project.creator)
        )
        url = self.project.web_url_for('project_wiki_edit_post', wname='home')
        res = self.app.post(url, {'content': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        # page was updated with new content
        new_wiki = self.project.get_wiki_page('home')
        assert_equal(new_wiki.content, 'new content')

    def test_project_wiki_edit_post_with_new_wname_and_no_content(self):
        # note: forward slashes not allowed in page_name
        page_name = fake.catch_phrase().replace('/', ' ')

        old_wiki_page_count = NodeWikiPage.find().count()
        url = self.project.web_url_for('project_wiki_edit_post', wname=page_name)
        # User submits to edit form with no content
        res = self.app.post(url, {'content': ''}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        new_wiki_page_count = NodeWikiPage.find().count()
        # A new wiki page was created in the db
        assert_equal(new_wiki_page_count, old_wiki_page_count + 1)

        # Node now has the new wiki page associated with it
        self.project.reload()
        new_page = self.project.get_wiki_page(page_name)
        assert_is_not_none(new_page)

    def test_project_wiki_edit_post_with_new_wname_and_content(self):
        # note: forward slashes not allowed in page_name
        page_name = fake.catch_phrase().replace('/' , ' ')
        page_content = fake.bs()

        old_wiki_page_count = NodeWikiPage.find().count()
        url = self.project.web_url_for('project_wiki_edit_post', wname=page_name)
        # User submits to edit form with no content
        res = self.app.post(url, {'content': page_content}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        new_wiki_page_count = NodeWikiPage.find().count()
        # A new wiki page was created in the db
        assert_equal(new_wiki_page_count, old_wiki_page_count + 1)

        # Node now has the new wiki page associated with it
        self.project.reload()
        new_page = self.project.get_wiki_page(page_name)
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
        wiki = self.project.get_wiki_page(new_wname)
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
        wiki = self.project.get_wiki_page(new_wname)
        assert_equal(wiki.page_name, new_wname)
        assert_equal(wiki.content, new_wiki_content)
        assert_equal(res.status_code, 200)

    def test_wiki_edit_get_home(self):
        url = self.project.web_url_for('project_wiki_view', wname='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_view_scope(self):
        self.project.update_node_wiki('home', 'Version 1', Auth(self.user))
        self.project.update_node_wiki('home', 'Version 2', Auth(self.user))
        self.project.save()
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
        self.project.update_node_wiki('home', 'updated content', Auth(self.user))
        self.project.save()
        url = self.project.web_url_for('project_wiki_view', wname='home') + '?compare'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_compare_scope(self):
        self.project.update_node_wiki('home', 'Version 1', Auth(self.user))
        self.project.update_node_wiki('home', 'Version 2', Auth(self.user))
        self.project.save()
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
        wiki = self.project.get_wiki_page('cupcake')
        assert_is_not_none(wiki)

    def test_wiki_validate_name(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='Capslock')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_wiki_validate_name_cannot_create_home(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='home')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_project_wiki_validate_name_mixed_casing(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='CaPsLoCk')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_not_in('capslock', self.project.wiki_pages_current)
        self.project.update_node_wiki('CaPsLoCk', 'hello', self.consolidate_auth)
        assert_in('capslock', self.project.wiki_pages_current)

    def test_project_wiki_validate_name_diplay_correct_capitalization(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='CaPsLoCk')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_in('CaPsLoCk', res)

    def test_project_wiki_validate_name_conflict_different_casing(self):
        url = self.project.api_url_for('project_wiki_validate_name', wname='CAPSLOCK')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.update_node_wiki('CaPsLoCk', 'hello', self.consolidate_auth)
        assert_in('capslock', self.project.wiki_pages_current)
        url = self.project.api_url_for('project_wiki_validate_name', wname='capslock')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_project_dashboard_shows_no_wiki_content_text(self):
        # Regression test for:
        # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1104
        project = ProjectFactory(creator=self.user)
        url = project.web_url_for('view_project')
        res = self.app.get(url, auth=self.user.auth)
        assert_in('No wiki content', res)

    def test_project_dashboard_wiki_wname_get_shows_non_ascii_characters(self):
        # Regression test for:
        # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1104
        text = u'你好'
        self.project.update_node_wiki('home', text, Auth(self.user))

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
        self.project.update_node_wiki(name, 'some content', Auth(self.project.creator))
        page = self.project.get_wiki_page(name)
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
        url = self.project.api_url_for('wiki_widget', wid='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_is_none(res.json['wiki_content'])

    def test_wiki_widget_short_content_no_cutoff(self):
        short_content = 'a' * 150
        self.project.update_node_wiki('home', short_content, Auth(self.user))
        url = self.project.api_url_for('wiki_widget', wid='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_in(short_content, res.json['wiki_content'])
        assert_not_in('...', res.json['wiki_content'])
        assert_false(res.json['more'])

    def test_wiki_widget_long_content_cutoff(self):
        long_content = 'a' * 600
        self.project.update_node_wiki('home', long_content, Auth(self.user))
        url = self.project.api_url_for('wiki_widget', wid='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_less(len(res.json['wiki_content']), 520)  # wiggle room for closing tags
        assert_in('...', res.json['wiki_content'])
        assert_true(res.json['more'])

    @mock.patch('website.addons.wiki.model.NodeWikiPage.rendered_before_update', new_callable=mock.PropertyMock)
    def test_wiki_widget_use_python_render(self, mock_rendered_before_update):
        # New pages use js renderer
        mock_rendered_before_update.return_value = False
        self.project.update_node_wiki('home', 'updated content', Auth(self.user))
        url = self.project.api_url_for('wiki_widget', wid='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_false(res.json['use_python_render'])

        # Old pages use python renderer
        mock_rendered_before_update.return_value = True
        res = self.app.get(url, auth=self.user.auth)
        assert_true(res.json['use_python_render'])

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


class TestViewHelpers(OsfTestCase):

    def setUp(self):
        super(TestViewHelpers, self).setUp()
        self.project = ProjectFactory()
        self.wname = 'New page'
        self.project.update_node_wiki(self.wname, 'some content', Auth(self.project.creator))

    def test_get_wiki_web_urls(self):
        urls = _get_wiki_web_urls(self.project, self.wname)
        assert_equal(urls['base'], self.project.web_url_for('project_wiki_home', _guid=True))
        assert_equal(urls['edit'], self.project.web_url_for('project_wiki_view', wname=self.wname, _guid=True))
        assert_equal(urls['home'], self.project.web_url_for('project_wiki_home', _guid=True))
        assert_equal(urls['page'], self.project.web_url_for('project_wiki_view', wname=self.wname, _guid=True))

    def test_get_wiki_api_urls(self):
        urls = _get_wiki_api_urls(self.project, self.wname)
        assert_equal(urls['base'], self.project.api_url_for('project_wiki_home'))
        assert_equal(urls['delete'], self.project.api_url_for('project_wiki_delete', wname=self.wname))
        assert_equal(urls['rename'], self.project.api_url_for('project_wiki_rename', wname=self.wname))
        assert_equal(urls['content'], self.project.api_url_for('wiki_page_content', wname=self.wname))


class TestWikiDelete(OsfTestCase):

    def setUp(self):
        super(TestWikiDelete, self).setUp()

        self.project = ProjectFactory(is_public=True)
        api_key = ApiKeyFactory()
        self.project.creator.api_keys.append(api_key)
        self.project.creator.save()
        self.consolidate_auth = Auth(user=self.project.creator, api_key=api_key)
        self.auth = ('test', api_key._primary_key)
        self.project.update_node_wiki('Elephants', 'Hello Elephants', self.consolidate_auth)
        self.project.update_node_wiki('Lions', 'Hello Lions', self.consolidate_auth)
        self.elephant_wiki = self.project.get_wiki_page('Elephants')
        self.lion_wiki = self.project.get_wiki_page('Lions')

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_project_wiki_delete(self, mock_shrejs):
        assert_in('elephants', self.project.wiki_pages_current)
        url = self.project.api_url_for(
            'project_wiki_delete',
            wname='elephants'
        )
        self.app.delete(
            url,
            auth=self.auth
        )
        self.project.reload()
        assert_not_in('elephants', self.project.wiki_pages_current)

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_project_wiki_delete_w_valid_special_characters(self, mock_sharejs):
        # TODO: Need to understand why calling update_node_wiki with failure causes transaction rollback issue later
        # with assert_raises(NameInvalidError):
        #     self.project.update_node_wiki(SPECIAL_CHARACTERS_ALL, 'Hello Special Characters', self.consolidate_auth)
        self.project.update_node_wiki(SPECIAL_CHARACTERS_ALLOWED, 'Hello Special Characters', self.consolidate_auth)
        self.special_characters_wiki = self.project.get_wiki_page(SPECIAL_CHARACTERS_ALLOWED)
        assert_in(to_mongo_key(SPECIAL_CHARACTERS_ALLOWED), self.project.wiki_pages_current)
        url = self.project.api_url_for(
            'project_wiki_delete',
            wname=SPECIAL_CHARACTERS_ALLOWED
        )
        self.app.delete(
            url,
            auth=self.auth
        )
        self.project.reload()
        assert_not_in(to_mongo_key(SPECIAL_CHARACTERS_ALLOWED), self.project.wiki_pages_current)


class TestWikiRename(OsfTestCase):

    def setUp(self):
        super(TestWikiRename, self).setUp()

        self.project = ProjectFactory(is_public=True)
        api_key = ApiKeyFactory()
        self.project.creator.api_keys.append(api_key)
        self.project.creator.save()
        self.consolidate_auth = Auth(user=self.project.creator, api_key=api_key)
        self.auth = ('test', api_key._primary_key)
        self.project.update_node_wiki('home', 'Hello world', self.consolidate_auth)

        self.page_name = 'page2'
        self.project.update_node_wiki(self.page_name, 'content', self.consolidate_auth)
        self.project.save()
        self.page = self.project.get_wiki_page(self.page_name)

        self.wiki = self.project.get_wiki_page('home')
        self.url = self.project.api_url_for(
            'project_wiki_rename',
            wname=self.page_name,
        )

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_rename_wiki_page_valid(self, mock_sharejs, new_name=u'away'):
        self.app.put_json(
            self.url,
            {'value': new_name},
            auth=self.auth
        )
        self.project.reload()

        old_wiki = self.project.get_wiki_page(self.page_name)
        assert_false(old_wiki)

        new_wiki = self.project.get_wiki_page(new_name)
        assert_true(new_wiki)
        assert_equal(new_wiki._primary_key, self.page._primary_key)
        assert_equal(new_wiki.content, self.page.content)
        assert_equal(new_wiki.version, self.page.version)

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
        old_wiki = self.project.get_wiki_page(self.page_name)
        assert_true(old_wiki)

    def test_rename_wiki_page_duplicate(self):
        self.project.update_node_wiki('away', 'Hello world', self.consolidate_auth)
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
        project.update_node_wiki('Hello', 'hello world', Auth(user=user))
        url = project.api_url_for('project_wiki_rename', wname=to_mongo_key('Hello'))
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
        self.project.update_node_wiki(old_name, 'Hello world', self.consolidate_auth)
        res = self.app.put_json(
            self.url,
            {'value': new_name},
            auth=self.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 409)

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_rename_wiki_page_same_name_different_casing(self, mock_sharejs):
        old_name = 'away'
        new_name = 'AWAY'
        self.project.update_node_wiki(old_name, 'Hello world', self.consolidate_auth)
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

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_can_rename_to_a_deleted_page(self, mock_sharejs):
        self.project.delete_node_wiki(self.page_name, self.consolidate_auth)
        self.project.save()

        # Creates a new page
        self.project.update_node_wiki('page3' ,'moarcontent', self.consolidate_auth)
        self.project.save()

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
        wiki = NodeWikiFactory(
            content='[[wiki2]]',
            user=user,
            node=project,
        )
        assert_in(
            project.web_url_for('project_wiki_view', wname='wiki2'),
            wiki.html(project),
        )

    # Regression test for https://sentry.osf.io/osf/production/group/310/
    def test_bad_links(self):
        content = u'<span></span><iframe src="http://httpbin.org/"></iframe>'
        node = ProjectFactory()
        wiki = NodeWikiFactory(content=content, node=node)
        expected = render_content(content, node)
        assert_equal(expected, wiki.html(node))


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
        self.project.update_node_wiki(self.wname, 'some content', Auth(self.user))
        self.project.save()

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
        self.project.update_node_wiki(self.wname, 'some content', Auth(self.user))
        self.project.save()

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

        # uuids are stored the same internally
        assert_equal(
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

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_migration_does_not_affect_forks(self, mock_sharejs):
        original_uuid = generate_private_uuid(self.project, self.wname)
        self.project.update_node_wiki(self.wname, 'Hello world', Auth(self.user))
        fork = self.project.fork_node(Auth(self.user))
        assert_equal(original_uuid, fork.wiki_private_uuids.get(self.wkey))

        migrate_uuid(self.project, self.wname)

        assert_not_equal(original_uuid, self.project.wiki_private_uuids.get(self.wkey))
        assert_equal(original_uuid, fork.wiki_private_uuids.get(self.wkey))

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_uuid_persists_after_delete(self, mock_sharejs):
        assert_is_none(self.project.wiki_private_uuids.get(self.wkey))

        # Create wiki page
        self.project.update_node_wiki(self.wname, 'Hello world', Auth(self.user))

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

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_uuid_persists_after_rename(self, mock_sharejs):
        new_wname = 'bar.baz'
        new_wkey = to_mongo_key(new_wname)
        assert_is_none(self.project.wiki_private_uuids.get(self.wkey))
        assert_is_none(self.project.wiki_private_uuids.get(new_wkey))

        # Create wiki page
        self.project.update_node_wiki(self.wname, 'Hello world', Auth(self.user))
        wiki_page = self.project.get_wiki_page(self.wname)

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
        self.project.update_node_wiki(self.wname, 'Hello world', Auth(self.user))
        self.wiki_page = self.project.get_wiki_page(self.wname)

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

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
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

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_migrate_uuid_no_mongo(self, mock_sharejs):
        # Case where no edits have been made to the wiki
        wname = 'bar.baz'
        wkey = to_mongo_key(wname)
        share_uuid = generate_private_uuid(self.project, wname)
        sharejs_uuid = get_sharejs_uuid(self.project, wname)

        self.project.update_node_wiki(wname, 'Hello world', Auth(self.user))
        wiki_page = self.project.get_wiki_page(wname)
        migrate_uuid(self.project, wname)

        assert_not_equal(share_uuid, self.project.wiki_private_uuids.get(wkey))
        assert_is_none(self.db.docs.find_one({'_id': sharejs_uuid}))
        assert_is_none(self.db.docs_ops.find_one({'name': sharejs_uuid}))

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_migrate_uuid_updates_node(self, mock_sharejs):
        migrate_uuid(self.project, self.wname)
        assert_not_equal(self.private_uuid, self.project.wiki_private_uuids[self.wkey])

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_manage_contributors_updates_uuid(self, mock_sharejs):
        user = UserFactory()
        self.project.add_contributor(
            contributor=user,
            permissions=['read', 'write', 'admin'],
            auth=Auth(user=self.user),
        )
        self.project.save()
        assert_equal(self.private_uuid, self.project.wiki_private_uuids[self.wkey])
        # Removing admin permission does nothing
        self.project.manage_contributors(
            user_dicts=[
                {'id': user._id, 'permission': 'write', 'visible': True},
                {'id': self.user._id, 'permission': 'admin', 'visible': True},
            ],
            auth=Auth(user=self.user),
            save=True,
        )
        assert_equal(self.private_uuid, self.project.wiki_private_uuids[self.wkey])
        # Removing write permission migrates uuid
        self.project.manage_contributors(
            user_dicts=[
                {'id': user._id, 'permission': 'read', 'visible': True},
                {'id': self.user._id, 'permission': 'admin', 'visible': True},
            ],
            auth=Auth(user=self.user),
            save=True,
        )
        assert_not_equal(self.private_uuid, self.project.wiki_private_uuids[self.wkey])


    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
    def test_delete_share_doc(self, mock_sharejs):
        delete_share_doc(self.project, self.wname)
        assert_is_none(self.db.docs.find_one({'_id': self.sharejs_uuid}))
        assert_is_none(self.db.docs_ops.find_one({'name': self.sharejs_uuid}))

    @mock.patch('website.addons.wiki.utils.broadcast_to_sharejs')
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

