# -*- coding: utf-8 -*-

# PEP8 asserts
import httplib as http

from nose.tools import *  # noqa
from modularodm.exceptions import ValidationValueError

from tests.base import OsfTestCase, fake
from tests.factories import (
    UserFactory, NodeFactory, PointerFactory, ProjectFactory, ApiKeyFactory,
    AuthUserFactory, NodeWikiFactory,
)

from website import settings
from website.addons.wiki.views import _serialize_wiki_toc, _get_wiki_web_urls, _get_wiki_api_urls
from website.addons.wiki.model import NodeWikiPage, render_content
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
        url = self.project.web_url_for('project_wiki_page', wname='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_url_for_pointer_returns_200(self):
        # TODO: explain how this tests a pointer
        project = ProjectFactory(is_public=True)
        self.project.add_pointer(project, Auth(self.project.creator), save=True)
        url = self.project.web_url_for('project_wiki_page', wname='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_content_returns_200(self):
        node = ProjectFactory(is_public=True)
        url = node.api_url_for('wiki_page_content', wname='somerandomid')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_url_for_component_returns_200(self):
        component = NodeFactory(project=self.project, is_public=True)
        url = component.web_url_for('project_wiki_page', wname='home')
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
            pointed_node.web_url_for('project_wiki_page', wname='home', _guid=True)
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
        page_name = fake.catch_phrase()

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
        page_name, page_content = fake.catch_phrase(), fake.bs()

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
        url = self.project.web_url_for('project_wiki_edit', wname='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_compare_returns_200(self):
        self.project.update_node_wiki('home', 'updated content', Auth(self.user))
        self.project.save()
        url = self.project.web_url_for('project_wiki_compare', wname='home', wver=1)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_compare_with_invalid_wname(self):
        url = self.project.web_url_for('project_wiki_compare', wname='this-doesnt-exist', wver=1)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_wiki_page_creation_strips_whitespace(self):
        # Regression test for:
        # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1080
        # wname has a trailing space
        url = self.project.web_url_for('project_wiki_edit', wname='cupcake ')
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
        # page_url = self.project.api_url_for('project_wiki_page', wname='home')
        # assert_in(page_url, res.location)

    def test_project_wiki_home_web_route(self):
        page_url = self.project.web_url_for('project_wiki_page', wname='home', _guid=True)
        url = self.project.web_url_for('project_wiki_home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.status_code, 302)
        assert_in(page_url, res.location)

    def test_wiki_id_url_get_returns_302_and_resolves(self):
        name = 'page by id'
        self.project.update_node_wiki(name, 'some content', Auth(self.project.creator))
        page = self.project.get_wiki_page(name)
        page_url = self.project.web_url_for('project_wiki_page', wname=page.page_name, _guid=True)
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


class TestViewHelpers(OsfTestCase):

    def setUp(self):
        super(TestViewHelpers, self).setUp()
        self.project = ProjectFactory()
        self.wname = 'New page'
        self.project.update_node_wiki(self.wname, 'some content', Auth(self.project.creator))

    def test_get_wiki_web_urls(self):
        urls = _get_wiki_web_urls(self.project, self.wname)
        assert_equal(urls['compare'], self.project.web_url_for('project_wiki_compare',
                wname=self.wname, wver=1, _guid=True))
        assert_equal(urls['edit'], self.project.web_url_for('project_wiki_edit', wname=self.wname, _guid=True))
        assert_equal(urls['home'], self.project.web_url_for('project_wiki_home', _guid=True))
        assert_equal(urls['page'], self.project.web_url_for('project_wiki_page', wname=self.wname, _guid=True))

    def test_get_wiki_api_urls(self):
        urls = _get_wiki_api_urls(self.project, self.wname)
        assert_equal(urls['delete'], self.project.api_url_for('project_wiki_delete', wname=self.wname))
        assert_equal(urls['rename'], self.project.api_url_for('project_wiki_rename', wname=self.wname))


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
            wname='elephants'
        )
        self.app.delete(
            url,
            auth=self.auth
        )
        self.project.reload()
        assert_not_in('elephants', self.project.wiki_pages_current)

    def test_project_wiki_delete_w_valid_special_characters(self):
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

    def test_rename_wiki_page_valid(self, new_name=u'away'):
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

    def test_rename_wiki_page_same_name_different_casing(self):
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

    def test_can_rename_to_a_deleted_page(self):
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
            project.web_url_for('project_wiki_page', wname='wiki2'),
            wiki.html(project),
        )

    # Regression test for https://sentry.osf.io/osf/production/group/310/
    def test_bad_links(self):
        content = u'<span></span><iframe src="http://httpbin.org/"></iframe>'
        node = ProjectFactory()
        wiki = NodeWikiFactory(content=content, node=node)
        expected = render_content(content, node)
        assert_equal(expected, wiki.html(node))


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

        url_v1_to_v2 = self.project.web_url_for('project_wiki_compare', wname='home', wver=1)
        res = self.app.get(url_v1_to_v2)
        comparison_v1_to_v2 = \
            '<span style="background:#D16587; font-size:1.5em;">h</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">H</span>ello ' \
            '<span style="background:#D16587; font-size:1.5em;">w</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">W</span>orld'
        assert_equal(res.status_int, http.OK)
        assert_true(comparison_v1_to_v2 in res.body)

        url_v2_to_v2 = self.project.web_url_for('project_wiki_compare', wname='home', wver=2)
        res = self.app.get(url_v2_to_v2)
        comparison_v2_to_v2 = 'Hello World'
        assert_equal(res.status_int, http.OK)
        assert_true(comparison_v2_to_v2 in res.body)

    def test_compare_wiki_page_sanitized(self):
        content_js_script = '<script>alert(''a problem'');</script>'
        self.project.update_node_wiki('home', content_js_script, self.consolidate_auth)

        url_v1_to_v2 = self.project.web_url_for('project_wiki_compare', wname='home', wver=1)
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

        url_v2_to_v2 = self.project.web_url_for('project_wiki_compare', wname='home', wver=2)
        res = self.app.get(url_v2_to_v2)
        comparison_v2_to_v2 = '&lt;script&gt;alert(''a problem'');&lt;/script&gt;'
        assert_equal(res.status_int, http.OK)
        assert_true(content_js_script not in res.body)
        assert_true(comparison_v2_to_v2 in res.body)
