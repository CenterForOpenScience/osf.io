# -*- coding: utf-8 -*-

# PEP8 asserts
from copy import deepcopy
import httplib as http
import uuid
import unittest

from nose.tools import *  # noqa
from modularodm.exceptions import ValidationValueError

from tests.base import OsfTestCase, fake
from tests.factories import (
    UserFactory, NodeFactory, PointerFactory, ProjectFactory, ApiKeyFactory,
    AuthUserFactory, NodeWikiFactory,
)

from website.addons.wiki.views import serialize_wiki_toc, _get_wiki_web_urls, _get_wiki_api_urls
from website.addons.wiki.model import NodeWikiPage
from website.addons.wiki.utils import (
    docs_uuid, generate_share_uuid, share_db, ops_uuid
)
from website.addons.wiki.tests.config import EXAMPLE_DOCS, EXAMPLE_OPS, EXAMPLE_OPS_SHORT
from framework.auth import Auth
from framework.mongo.utils import to_mongo_key

SPECIAL_CHARACTERS = u'`~!@#$%^*()-=_+ []{}\|/?.df,;:''"'


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
        url = self.project.web_url_for('project_wiki_page', wid='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_url_for_pointer_returns_200(self):
        # TODO: explain how this tests a pointer
        project = ProjectFactory(is_public=True)
        self.project.add_pointer(project, Auth(self.project.creator), save=True)
        url = self.project.web_url_for('project_wiki_page', wid='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_content_returns_200(self):
        node = ProjectFactory(is_public=True)
        url = node.api_url_for('wiki_page_content', wid='somerandomid')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_url_for_component_returns_200(self):
        component = NodeFactory(project=self.project, is_public=True)
        url = component.web_url_for('project_wiki_page', wid='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_serialize_wiki_toc(self):
        project = ProjectFactory()
        auth = Auth(project.creator)
        NodeFactory(project=project, creator=project.creator)
        no_wiki = NodeFactory(project=project, creator=project.creator)
        project.save()

        serialized = serialize_wiki_toc(project, auth=auth)
        assert_equal(len(serialized), 2)
        no_wiki.delete_addon('wiki', auth=auth)
        serialized = serialize_wiki_toc(project, auth=auth)
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

        serialized = serialize_wiki_toc(project, auth)
        assert_equal(
            serialized[0]['url'],
            pointed_node.web_url_for('project_wiki_page', wid='home', _guid=True)
        )

    def test_project_wiki_edit_post(self):
        self.project.update_node_wiki(
            'home',
            content='old content',
            auth=Auth(self.project.creator)
        )
        url = self.project.web_url_for('project_wiki_edit_post', wid='home')
        res = self.app.post(url, {'content': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        # page was updated with new content
        new_wiki = self.project.get_wiki_page('home')
        assert_equal(new_wiki.content, 'new content')

    def test_project_wiki_edit_post_with_new_wid_and_no_content(self):
        page_name = fake.catch_phrase()

        old_wiki_page_count = NodeWikiPage.find().count()
        url = self.project.web_url_for('project_wiki_edit_post', wid=page_name)
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

    def test_project_wiki_edit_post_with_new_wid_and_content(self):
        page_name, page_content = fake.catch_phrase(), fake.bs()

        old_wiki_page_count = NodeWikiPage.find().count()
        url = self.project.web_url_for('project_wiki_edit_post', wid=page_name)
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
        # wid doesn't exist in the db, so it will be created
        new_wid = u'øˆ∆´ƒøßå√ß'
        url = self.project.web_url_for('project_wiki_edit_post', wid=new_wid)
        res = self.app.post(url, {'content': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        wiki = self.project.get_wiki_page(new_wid)
        assert_equal(wiki.page_name, new_wid)

        # updating content should return correct url as well.
        res = self.app.post(url, {'content': 'updated content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

    def test_project_wiki_edit_post_with_special_characters(self):
        new_wid = 'title: ' + SPECIAL_CHARACTERS
        new_wiki_content = 'content: ' + SPECIAL_CHARACTERS
        url = self.project.web_url_for('project_wiki_edit_post', wid=new_wid)
        res = self.app.post(url, {'content': new_wiki_content}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        wiki = self.project.get_wiki_page(new_wid)
        assert_equal(wiki.page_name, new_wid)
        assert_equal(wiki.content, new_wiki_content)
        assert_equal(res.status_code, 200)

    def test_wiki_edit_get_home(self):
        url = self.project.web_url_for('project_wiki_edit', wid='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_compare_returns_200(self):
        self.project.update_node_wiki('home', 'updated content', Auth(self.user))
        self.project.save()
        url = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=1)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_compare_with_invalid_wid(self):
        url = self.project.web_url_for('project_wiki_compare', wid='this-doesnt-exist', compare_id=1)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_wiki_page_creation_strips_whitespace(self):
        # Regression test for:
        # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1080
        # wid has a trailing space
        url = self.project.web_url_for('project_wiki_edit', wid='cupcake ')
        res = self.app.post(url, {'content': 'blah'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        self.project.reload()
        wiki = self.project.get_wiki_page('cupcake')
        assert_is_not_none(wiki)

    def test_wiki_validate_name(self):
        url = self.project.api_url_for('project_wiki_validate_name', wid='Capslock')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_validate_name_mixed_casing(self):
        url = self.project.api_url_for('project_wiki_validate_name', wid='CaPsLoCk')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_not_in('capslock', self.project.wiki_pages_current)
        self.project.update_node_wiki('CaPsLoCk', 'hello', self.consolidate_auth)
        assert_in('capslock', self.project.wiki_pages_current)

    def test_project_wiki_validate_name_diplay_correct_capitalization(self):
        url = self.project.api_url_for('project_wiki_validate_name', wid='CaPsLoCk')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_in('CaPsLoCk', res)

    def test_project_wiki_validate_name_conflict_different_casing(self):
        url = self.project.api_url_for('project_wiki_validate_name', wid='CAPSLOCK')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.update_node_wiki('CaPsLoCk', 'hello', self.consolidate_auth)
        assert_in('capslock', self.project.wiki_pages_current)
        url = self.project.api_url_for('project_wiki_validate_name', wid='capslock')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_project_dashboard_shows_no_wiki_content_text(self):
        # Regression test for:
        # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1104
        project = ProjectFactory(creator=self.user)
        url = project.web_url_for('view_project')
        res = self.app.get(url, auth=self.user.auth)
        assert_in('No wiki content', res)

    def test_project_dashboard_wiki_widget_shows_non_ascii_characters(self):
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
        assert_equals(res.status_code, 200)

    def test_project_wiki_home_web_route(self):
        url = self.project.web_url_for('project_wiki_home')
        res = self.app.get(url, auth=self.user.auth)
        assert_in('home', res)


class TestViewHelpers(OsfTestCase):

    def setUp(self):
        super(TestViewHelpers, self).setUp()
        self.project = ProjectFactory()
        self.wid = 'New page'
        self.project.update_node_wiki(self.wid, 'some content', Auth(self.project.creator))

    def test_get_wiki_web_urls(self):
        urls = _get_wiki_web_urls(self.project, self.wid)
        assert_equal(urls['compare'], self.project.web_url_for('project_wiki_compare',
                wid=self.wid, compare_id=1, _guid=True))
        assert_equal(urls['edit'], self.project.web_url_for('project_wiki_edit', wid=self.wid, _guid=True))
        assert_equal(urls['home'], self.project.web_url_for('project_wiki_home', _guid=True))
        assert_equal(urls['page'], self.project.web_url_for('project_wiki_page', wid=self.wid, _guid=True))

    def test_get_wiki_api_urls(self):
        urls = _get_wiki_api_urls(self.project, self.wid)
        assert_equal(urls['delete'], self.project.api_url_for('project_wiki_delete', wid=self.wid))
        assert_equal(urls['rename'], self.project.api_url_for('project_wiki_rename', wid=self.wid))


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

    def test_project_wiki_delete(self):
        assert_in('elephants', self.project.wiki_pages_current)
        url = self.project.api_url_for(
            'project_wiki_delete',
            wid='elephants'
        )
        self.app.delete(
            url,
            auth=self.auth
        )
        self.project.reload()
        assert_not_in('elephants', self.project.wiki_pages_current)

    def test_project_wiki_delete_w_special_characters(self):
        self.project.update_node_wiki(SPECIAL_CHARACTERS, 'Hello Special Characters', self.consolidate_auth)
        self.special_characters_wiki = self.project.get_wiki_page(SPECIAL_CHARACTERS)
        assert_in(to_mongo_key(SPECIAL_CHARACTERS), self.project.wiki_pages_current)
        url = self.project.api_url_for(
            'project_wiki_delete',
            wid=SPECIAL_CHARACTERS
        )
        self.app.delete(
            url,
            auth=self.auth
        )
        self.project.reload()
        assert_not_in(to_mongo_key(SPECIAL_CHARACTERS), self.project.wiki_pages_current)


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
            wid=self.wiki._id,
        )

    def test_rename_wiki_page_valid(self, new_name=u'away'):
        self.app.put_json(
            self.url,
            {'value': new_name, 'pk': self.page._id},
            auth=self.auth
        )
        self.project.reload()

        old_wiki = self.project.get_wiki_page(self.page_name)
        assert_false(old_wiki)

        new_wiki = self.project.get_wiki_page(new_name)
        assert_true(new_wiki)
        assert_equal(new_wiki._id, self.page._id)
        assert_equal(new_wiki.content, self.page.content)
        assert_equal(new_wiki.version, self.page.version)

    def test_rename_wiki_page_duplicate(self):
        self.project.update_node_wiki('away', 'Hello world', self.consolidate_auth)
        new_name = 'away'

        res = self.app.put_json(
            self.url,
            {'value': new_name, 'pk': self.page._id},
            auth=self.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 409)

    def test_rename_wiki_invalid_pk(self):
        # pk is invalid
        res = self.app.put_json(self.url, {'value': 'newname', 'pk': 'notavalidpk'},
            auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_rename_wiki_pk_with_pk_missing(self):
        # pk is missing
        res = self.app.put_json(self.url, {'value': 'newname'}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_rename_wiki_pk_with_value_missing(self):
        # value is missing
        res = self.app.put_json(self.url, {'pk': self.page._id}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_rename_wiki_page_duplicate_different_casing(self):
        self.project.update_node_wiki('away', 'Hello world', self.consolidate_auth)
        new_name = 'AwAy'

        res = self.app.put_json(
            self.url,
            {'value': new_name, 'pk': self.page._id},
            auth=self.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 409)

    def test_rename_wiki_page_same_name_different_casing(self):
        self.project.update_node_wiki('away', 'Hello world', self.consolidate_auth)
        new_name = 'AWAY'
        page = self.project.get_wiki_page('away')

        res = self.app.put_json(
            self.url,
            {'value': new_name, 'pk': page._id},
            auth=self.auth,
            expect_errors=False
        )
        assert_equal(res.status_code, 200)

    def test_cannot_rename_home_page(self):
        home = self.project.get_wiki_page('home')
        res = self.app.put_json(self.url, {'value': 'homelol', 'pk': home._id}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_can_rename_to_a_deleted_page(self):
        self.project.delete_node_wiki(self.project, self.page, self.consolidate_auth)
        self.project.save()

        # Creates a new page
        self.project.update_node_wiki('page3' ,'moarcontent', self.consolidate_auth)
        page3 = self.project.get_wiki_page('page3')
        self.project.save()

        url = self.project.api_url_for('project_wiki_rename', wid='page3')
        # Renames the wiki to the deleted page
        res = self.app.put_json(self.url, {'value': self.page_name, 'pk': page3._id}, auth=self.auth)
        assert_equal(res.status_code, 200)

    def test_rename_wiki_page_with_html_title(self):
        # script is not an issue since data is sanitized via bleach or mako before display.
        self.test_rename_wiki_page_valid(new_name=u'<html>hello</html')

    def test_rename_wiki_page_with_non_ascii_title(self):
        self.test_rename_wiki_page_valid(new_name=u'øˆ∆´ƒøßå√ß')

    def test_rename_wiki_page_with_special_character_title(self):
        self.test_rename_wiki_page_valid(new_name=SPECIAL_CHARACTERS)


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
            project.web_url_for('project_wiki_page', wid='wiki2'),
            wiki.html(project),
        )


class TestWikiCompare(OsfTestCase):

    def setUp(self):
        super(TestWikiCompare, self).setUp()

        self.project = ProjectFactory(is_public=True)
        api_key = ApiKeyFactory()
        self.project.creator.api_keys.append(api_key)
        self.project.creator.save()
        self.consolidate_auth = Auth(user=self.project.creator, api_key=api_key)
        self.auth = ('test', api_key._primary_key)
        self.project.update_node_wiki('home', 'hello world', self.consolidate_auth)
        self.wiki = self.project.get_wiki_page('home')

    def test_compare_wiki_page_valid(self):
        self.project.update_node_wiki('home', 'Hello World', self.consolidate_auth)

        url_v1_to_v2 = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=1)
        res = self.app.get(url_v1_to_v2)
        comparison_v1_to_v2 = \
            '<span style="background:#D16587; font-size:1.5em;">h</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">H</span>ello ' \
            '<span style="background:#D16587; font-size:1.5em;">w</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">W</span>orld'
        assert_equal(res.status_int, http.OK)
        assert_true(comparison_v1_to_v2 in res.body)

        url_v2_to_v2 = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=2)
        res = self.app.get(url_v2_to_v2)
        comparison_v2_to_v2 = 'Hello World'
        assert_equal(res.status_int, http.OK)
        assert_true(comparison_v2_to_v2 in res.body)

    def test_compare_wiki_page_sanitized(self):
        content_js_script = '<script>alert(''a problem'');</script>'
        self.project.update_node_wiki('home', content_js_script, self.consolidate_auth)

        url_v1_to_v2 = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=1)
        res = self.app.get(url_v1_to_v2)
        comparison_v1_to_v2 = \
            '<span style="background:#D16587; font-size:1.5em;">h</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">&lt;script&gt;al</span>e' \
            '<span style="background:#4AA02C; font-size:1.5em; ">rt(''a prob</span>l' \
            '<span style="background:#D16587; font-size:1.5em;">lo wo</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">em'');</span>r' \
            '<span style="background:#D16587; font-size:1.5em;">ld</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">ipt&gt;</span>'
        assert_equal(res.status_int, http.OK)
        assert_true(content_js_script not in res.body)
        assert_true(comparison_v1_to_v2 in res.body)

        url_v2_to_v2 = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=2)
        res = self.app.get(url_v2_to_v2)
        comparison_v2_to_v2 = '&lt;script&gt;alert(''a problem'');&lt;/script&gt;'
        assert_equal(res.status_int, http.OK)
        assert_true(content_js_script not in res.body)
        assert_true(comparison_v2_to_v2 in res.body)


class TestWikiShareJS(OsfTestCase):

    def setUp(self):
        super(TestWikiShareJS, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)

    def test_uuid_generated(self):
        wid = 'foo'
        assert_is_none(self.project.wiki_sharejs_uuids.get(wid))
        url = self.project.web_url_for('project_wiki_edit', wid=wid)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        self.project.reload()
        assert_true(self.project.wiki_sharejs_uuids.get(wid))
        assert_not_in(self.project.wiki_sharejs_uuids.get(wid), res.body)
        assert_in(docs_uuid(self.project, self.project.wiki_sharejs_uuids.get(wid)), res.body)

    def test_uuids_differ_between_pages(self):
        wid1 = 'foo'
        url1 = self.project.web_url_for('project_wiki_edit', wid=wid1)
        res1 = self.app.get(url1, auth=self.user.auth)
        assert_equal(res1.status_code, 200)

        wid2 = 'bar'
        url2 = self.project.web_url_for('project_wiki_edit', wid=wid2)
        res2 = self.app.get(url2, auth=self.user.auth)
        assert_equal(res2.status_code, 200)

        self.project.reload()
        uuid1 = docs_uuid(self.project, self.project.wiki_sharejs_uuids.get(wid1))
        uuid2 = docs_uuid(self.project, self.project.wiki_sharejs_uuids.get(wid2))

        assert_not_equal(uuid1, uuid2)
        assert_in(uuid1, res1)
        assert_in(uuid2, res2)
        assert_not_in(uuid1, res2)
        assert_not_in(uuid2, res1)

    def test_uuids_differ_between_forks(self):
        wid = 'foo'
        url = self.project.web_url_for('project_wiki_edit', wid=wid)
        project_res = self.app.get(url, auth=self.user.auth)
        assert_equal(project_res.status_code, 200)
        self.project.reload()

        fork = self.project.fork_node(Auth(self.user))
        assert_true(fork.is_fork_of(self.project))
        fork_url = fork.web_url_for('project_wiki_edit', wid=wid)
        fork_res = self.app.get(fork_url, auth=self.user.auth)
        assert_equal(fork_res.status_code, 200)
        fork.reload()

        # uuids are stored the same internally
        assert_equal(
            self.project.wiki_sharejs_uuids.get(wid),
            fork.wiki_sharejs_uuids.get(wid)
        )

        project_uuid = docs_uuid(self.project, self.project.wiki_sharejs_uuids.get(wid))
        fork_uuid = docs_uuid(fork, fork.wiki_sharejs_uuids.get(wid))

        assert_not_equal(project_uuid, fork_uuid)
        assert_in(project_uuid, project_res)
        assert_in(fork_uuid, fork_res)
        assert_not_in(project_uuid, fork_res)
        assert_not_in(fork_uuid, project_res)

    def test_uuid_persists_after_delete(self):
        wid = 'foo'
        assert_is_none(self.project.wiki_sharejs_uuids.get(wid))

        # Create wiki page
        self.project.update_node_wiki(wid, 'Hello world', Auth(self.user))

        # Visit wiki edit page
        edit_url = self.project.web_url_for('project_wiki_edit', wid=wid)
        res = self.app.get(edit_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        original_uuid = self.project.wiki_sharejs_uuids.get(wid)

        # Delete wiki
        delete_url = self.project.api_url_for('project_wiki_delete', wid=wid)
        res = self.app.delete(delete_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(original_uuid, self.project.wiki_sharejs_uuids.get(wid))

        # Revisit wiki edit page
        res = self.app.get(edit_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(original_uuid, self.project.wiki_sharejs_uuids.get(wid))
        assert_in(docs_uuid(self.project, original_uuid), res.body)

    def test_uuid_persists_after_rename(self):
        original_wid = 'foo'
        new_wid = 'bar'
        assert_is_none(self.project.wiki_sharejs_uuids.get(original_wid))
        assert_is_none(self.project.wiki_sharejs_uuids.get(new_wid))

        # Create wiki page
        self.project.update_node_wiki(original_wid, 'Hello world', Auth(self.user))
        wiki_page = self.project.get_wiki_page(original_wid)

        # Visit wiki edit page
        original_edit_url = self.project.web_url_for('project_wiki_edit', wid=original_wid)
        res = self.app.get(original_edit_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        original_uuid = self.project.wiki_sharejs_uuids.get(original_wid)

        # Rename wiki
        rename_url = self.project.api_url_for('project_wiki_rename', wid=original_wid)
        res = self.app.put_json(
            rename_url,
            {'value': new_wid, 'pk': wiki_page._id},
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_is_none(self.project.wiki_sharejs_uuids.get(original_wid))
        assert_equal(original_uuid, self.project.wiki_sharejs_uuids.get(new_wid))

        # Revisit original wiki edit page
        res = self.app.get(original_edit_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_not_equal(original_uuid, self.project.wiki_sharejs_uuids.get(original_wid))
        assert_not_in(docs_uuid(self.project, original_uuid), res.body)


class TestWikiShareJSMongo(OsfTestCase):

    def setUp(self):
        super(TestWikiShareJSMongo, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.wid = 'foo'
        self.share_uuid = generate_share_uuid(self.project, self.wid)
        self.docs_uuid = docs_uuid(self.project, self.share_uuid)
        self.ops_uuid = ops_uuid(self.project, self.share_uuid)

        # Create wiki page
        self.project.update_node_wiki(self.wid, 'Hello world', Auth(self.user))
        self.wiki_page = self.project.get_wiki_page(self.wid)

        # Insert mongo data for current project/wiki
        self.db = share_db()
        docs = deepcopy(EXAMPLE_DOCS)
        docs['_id'] = self.docs_uuid
        self.db.docs.insert(docs)
        self.db[self.ops_uuid].insert(EXAMPLE_OPS)

    def test_migrate_uuid(self):
        self.wiki_page.migrate_uuid(self.project)
        assert_is_none(self.db['docs'].find_one({'_id': self.docs_uuid}))
        assert_is_none(self.db[self.ops_uuid].find_one())

        new_share_uuid = self.project.wiki_sharejs_uuids.get(self.wid)
        new_docs_uuid = docs_uuid(self.project, new_share_uuid)
        new_ops_uuid = ops_uuid(self.project, new_share_uuid)
        assert_equal(
            EXAMPLE_DOCS['data'],
            self.db['docs'].find_one({'_id': new_docs_uuid}).get('data')
        )
        assert_equal(
            EXAMPLE_OPS,
            [item for item in self.db[new_ops_uuid].find()]
        )

    def test_migrate_uuid_no_docs(self):
        wid = 'bar'
        share_uuid = generate_share_uuid(self.project, wid)
        original_ops_uuid = ops_uuid(self.project, share_uuid)

        self.project.update_node_wiki(wid, 'Hello world', Auth(self.user))
        wiki_page = self.project.get_wiki_page(wid)
        self.db[original_ops_uuid].insert(EXAMPLE_OPS_SHORT)

        wiki_page.migrate_uuid(self.project)
        new_share_uuid = self.project.wiki_sharejs_uuids.get(wid)
        # There is no item in docs because there were less than 20 ops
        new_ops_uuid = ops_uuid(self.project, new_share_uuid)

        assert_is_none(self.db[original_ops_uuid].find_one())
        assert_equal(
            EXAMPLE_OPS_SHORT,
            [item for item in self.db[new_ops_uuid].find()]
        )

        # tear down
        self.db.drop_collection(new_ops_uuid)
        assert_is_none(self.db[new_ops_uuid].find_one())

    @unittest.skip('Finish me!')
    def test_migrate_uuid_no_mongo(self):
        assert_true(False)

    def test_delete_share_document(self):
        self.wiki_page.delete_share_document(self.project)
        assert_is_none(self.db['docs'].find_one({'_id': self.docs_uuid}))
        assert_is_none(self.db[self.ops_uuid].find_one())

    def tearDown(self):
        super(TestWikiShareJSMongo, self).tearDown()
        self.db['docs'].remove({'_id': self.docs_uuid})
        self.db.drop_collection(self.ops_uuid)
        assert_is_none(self.db['docs'].find_one({'_id': self.docs_uuid}))
        assert_is_none(self.db[self.ops_uuid].find_one())


class TestWikiUtils(OsfTestCase):

    def setUp(self):
        super(TestWikiUtils, self).setUp()
        self.project = ProjectFactory()

    def test_docs_uuid(self):
        share_uuid = str(uuid.uuid1())

        # Provides consistent results
        assert_equal(docs_uuid(self.project, share_uuid), docs_uuid(self.project, share_uuid))

        # Provides obfuscation
        assert_not_in(share_uuid, docs_uuid(self.project, share_uuid))
        assert_not_in(docs_uuid(self.project, share_uuid), share_uuid)

        # Differs based on share uuid provided
        assert_not_equal(docs_uuid(self.project, share_uuid), self.project, str(uuid.uuid1()))

        # Differs across projects and forks
        project = ProjectFactory()
        fork = self.project.fork_node(Auth(self.project.creator))
        assert_not_equal(docs_uuid(self.project, share_uuid), docs_uuid(project, share_uuid))
        assert_not_equal(docs_uuid(self.project, share_uuid), docs_uuid(fork, share_uuid))

    def test_generate_share_uuid(self):
        wid = 'foo'
        assert_is_none(self.project.wiki_sharejs_uuids.get(wid))
        share_uuid = generate_share_uuid(self.project, wid)
        self.project.reload()
        assert_equal(self.project.wiki_sharejs_uuids[wid], share_uuid)

        new_uuid = generate_share_uuid(self.project, wid)
        self.project.reload()
        assert_not_equal(share_uuid, new_uuid)
        assert_equal(self.project.wiki_sharejs_uuids[wid], new_uuid)